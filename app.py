import os
import gradio as gr
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from supabase import create_client


# ============================================================
# Supabase 연결
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL과 SUPABASE_KEY 환경변수를 설정해주세요."
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# 한글 폰트
# ============================================================

font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams["font.family"] = "NanumGothic"

plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# 데이터 조회
# ============================================================

def get_assets():
    response = (
        supabase
        .table("assets")
        .select("*")
        .order("id")
        .execute()
    )

    return response.data or []


def get_transaction_data():
    response = (
        supabase
        .table("transactions")
        .select("*")
        .order("id")
        .execute()
    )

    return response.data or []


# ============================================================
# 현재 총 자산
# ============================================================

def get_total_asset():

    assets = get_assets()

    return sum(
        int(asset["money"])
        for asset in assets
    )


# ============================================================
# 자산 현황 출력
# ============================================================

def show_assets():

    assets = get_assets()

    result = ""

    for asset in assets:

        result += (
            f"{asset['name']} : "
            f"{int(asset['money']):,}원\n"
        )

    result += "----------------------\n"

    result += (
        f"총 자산 : "
        f"{get_total_asset():,}원"
    )

    return result


# ============================================================
# 자산 목록
# ============================================================

def get_asset_choices():

    assets = get_assets()

    return [
        asset["name"]
        for asset in assets
    ]


# ============================================================
# 월 목록
# ============================================================

def get_month_choices():

    transactions = get_transaction_data()

    months = set()

    for trans in transactions:

        date = dt.date.fromisoformat(
            trans["date"]
        )

        months.add(
            (
                date.year,
                date.month
            )
        )

    months = sorted(
        months,
        reverse=True
    )

    choices = ["전체"]

    for year, month in months:

        choices.append(
            f"{year}년 {month}월"
        )

    return choices


# ============================================================
# 거래내역 표
# ============================================================

def get_transactions():

    transactions = get_transaction_data()

    if not transactions:

        return pd.DataFrame(
            columns=[
                "번호",
                "날짜",
                "구분",
                "분류",
                "자산 종류",
                "금액"
            ]
        )

    data = []

    for trans in transactions:

        if trans["kind"] == "수입":

            amount = (
                f"+{int(trans['amount']):,}원"
            )

        else:

            amount = (
                f"-{int(trans['amount']):,}원"
            )

        data.append(
            [
                trans["id"],
                trans["date"],
                trans["kind"],
                trans["category"],
                trans["asset_name"],
                amount
            ]
        )

    return pd.DataFrame(
        data,
        columns=[
            "번호",
            "날짜",
            "구분",
            "분류",
            "자산 종류",
            "금액"
        ]
    )


# ============================================================
# 삭제할 거래 목록
# ============================================================

def get_transaction_choices():

    transactions = get_transaction_data()

    choices = []

    for trans in transactions:

        if trans["kind"] == "수입":
            sign = "+"
        else:
            sign = "-"

        label = (
            f"{trans['id']}. "
            f"{trans['date']} | "
            f"{trans['kind']} | "
            f"{trans['category']} | "
            f"{trans['asset_name']} | "
            f"{sign}{int(trans['amount']):,}원"
        )

        choices.append(
            (
                label,
                str(trans["id"])
            )
        )

    return choices


# ============================================================
# 거래 추가
# ============================================================

def add_transaction(
    kind,
    category,
    asset,
    amount
):

    if not category:

        return (
            "⚠ 분류를 입력해주세요.",
            f"{get_total_asset():,}원",
            show_assets(),
            get_transactions(),
            gr.update(
                choices=get_transaction_choices(),
                value=None
            ),
            gr.update(
                choices=get_month_choices()
            )
        )

    if amount is None or amount <= 0:

        return (
            "⚠ 올바른 금액을 입력해주세요.",
            f"{get_total_asset():,}원",
            show_assets(),
            get_transactions(),
            gr.update(
                choices=get_transaction_choices(),
                value=None
            ),
            gr.update(
                choices=get_month_choices()
            )
        )

    if not asset:

        return (
            "⚠ 먼저 자산을 추가하고 선택해주세요.",
            f"{get_total_asset():,}원",
            show_assets(),
            get_transactions(),
            gr.update(
                choices=get_transaction_choices(),
                value=None
            ),
            gr.update(
                choices=get_month_choices()
            )
        )

    amount = int(amount)

    # 자산 찾기
    assets = get_assets()

    selected_asset = None

    for item in assets:

        if item["name"] == asset:
            selected_asset = item
            break

    if selected_asset is None:

        return (
            "⚠ 선택한 자산을 찾을 수 없습니다.",
            f"{get_total_asset():,}원",
            show_assets(),
            get_transactions(),
            gr.update(
                choices=get_transaction_choices(),
                value=None
            ),
            gr.update(
                choices=get_month_choices()
            )
        )

    # 자산 금액 변경
    current_money = int(
        selected_asset["money"]
    )

    if kind == "수입":
        new_money = current_money + amount
    else:
        new_money = current_money - amount

    supabase \
        .table("assets") \
        .update(
            {"money": new_money}
        ) \
        .eq(
            "id",
            selected_asset["id"]
        ) \
        .execute()

    # 거래 저장
    supabase \
        .table("transactions") \
        .insert(
            {
                "date": str(dt.date.today()),
                "kind": kind,
                "category": category,
                "asset_name": asset,
                "amount": amount
            }
        ) \
        .execute()

    return (
        "✅ 거래가 저장되었습니다.",
        f"{get_total_asset():,}원",
        show_assets(),
        get_transactions(),
        gr.update(
            choices=get_transaction_choices(),
            value=None
        ),
        gr.update(
            choices=get_month_choices()
        )
    )


# ============================================================
# 거래 삭제
# ============================================================

def delete_transaction(selected_id):

    if selected_id is None:

        return (
            "⚠ 삭제할 거래를 선택해주세요.",
            f"{get_total_asset():,}원",
            show_assets(),
            get_transactions(),
            gr.update(
                choices=get_transaction_choices(),
                value=None
            ),
            gr.update(
                choices=get_month_choices()
            )
        )

    transaction_id = int(selected_id)

    # 거래 찾기
    transactions = get_transaction_data()

    selected_transaction = None

    for trans in transactions:

        if int(trans["id"]) == transaction_id:

            selected_transaction = trans
            break

    if selected_transaction is None:

        return (
            "⚠ 해당 거래를 찾을 수 없습니다.",
            f"{get_total_asset():,}원",
            show_assets(),
            get_transactions(),
            gr.update(
                choices=get_transaction_choices(),
                value=None
            ),
            gr.update(
                choices=get_month_choices()
            )
        )

    asset_name = selected_transaction[
        "asset_name"
    ]

    amount = int(
        selected_transaction["amount"]
    )

    # 자산 찾기
    assets = get_assets()

    selected_asset = None

    for asset in assets:

        if asset["name"] == asset_name:

            selected_asset = asset
            break

    if selected_asset is not None:

        current_money = int(
            selected_asset["money"]
        )

        # 수입 삭제 → 자산에서 빼기
        if selected_transaction["kind"] == "수입":

            new_money = current_money - amount

        # 지출 삭제 → 자산에 다시 더하기
        else:

            new_money = current_money + amount

        supabase \
            .table("assets") \
            .update(
                {"money": new_money}
            ) \
            .eq(
                "id",
                selected_asset["id"]
            ) \
            .execute()

    # 거래 삭제
    supabase \
        .table("transactions") \
        .delete() \
        .eq(
            "id",
            transaction_id
        ) \
        .execute()

    return (
        "🗑 거래가 삭제되었습니다.",
        f"{get_total_asset():,}원",
        show_assets(),
        get_transactions(),
        gr.update(
            choices=get_transaction_choices(),
            value=None
        ),
        gr.update(
            choices=get_month_choices()
        )
    )


# ============================================================
# 자산 추가
# ============================================================

def add_asset(
    asset_name,
    initial_money
):

    asset_name = (
        asset_name or ""
    ).strip()

    if not asset_name:

        return (
            "⚠ 자산 이름을 입력해주세요.",
            f"{get_total_asset():,}원",
            show_assets(),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            )
        )

    if asset_name in get_asset_choices():

        return (
            "⚠ 이미 존재하는 자산입니다.",
            f"{get_total_asset():,}원",
            show_assets(),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            )
        )

    money = int(
        initial_money or 0
    )

    if money < 0:

        return (
            "⚠ 초기 금액은 0원 이상으로 입력해주세요.",
            f"{get_total_asset():,}원",
            show_assets(),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            )
        )

    supabase \
        .table("assets") \
        .insert(
            {
                "name": asset_name,
                "money": money
            }
        ) \
        .execute()

    choices = get_asset_choices()

    return (
        f"✅ '{asset_name}'이(가) 추가되었습니다.",
        f"{get_total_asset():,}원",
        show_assets(),
        gr.update(
            choices=choices,
            value=asset_name
        ),
        gr.update(
            choices=choices
        ),
        gr.update(
            choices=choices
        )
    )


# ============================================================
# 자산 이름 변경
# ============================================================

def rename_asset(
    old_name,
    new_name
):

    new_name = (
        new_name or ""
    ).strip()

    if not old_name:

        return (
            "⚠ 변경할 자산을 선택해주세요.",
            show_assets(),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            )
        )

    if not new_name:

        return (
            "⚠ 새로운 이름을 입력해주세요.",
            show_assets(),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            )
        )

    if new_name in get_asset_choices():

        return (
            "⚠ 이미 존재하는 이름입니다.",
            show_assets(),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            )
        )

    # 자산 이름 변경
    supabase \
        .table("assets") \
        .update(
            {"name": new_name}
        ) \
        .eq(
            "name",
            old_name
        ) \
        .execute()

    # 기존 거래의 자산 이름도 변경
    supabase \
        .table("transactions") \
        .update(
            {"asset_name": new_name}
        ) \
        .eq(
            "asset_name",
            old_name
        ) \
        .execute()

    choices = get_asset_choices()

    return (
        f"✅ '{old_name}' → '{new_name}'으로 변경되었습니다.",
        show_assets(),
        gr.update(
            choices=choices,
            value=new_name
        ),
        gr.update(
            choices=choices,
            value=new_name
        ),
        gr.update(
            choices=choices
        )
    )


# ============================================================
# 자산 삭제
# ============================================================

def delete_asset(
    asset_name
):

    if not asset_name:

        return (
            "⚠ 삭제할 자산을 선택해주세요.",
            show_assets(),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            ),
            gr.update(
                choices=get_asset_choices()
            )
        )

    transactions = get_transaction_data()

    # 해당 자산을 사용한 거래가 있는지 확인
    for trans in transactions:

        if trans["asset_name"] == asset_name:

            return (
                "⚠ 거래내역이 존재하는 자산은 삭제할 수 없습니다.",
                show_assets(),
                gr.update(
                    choices=get_asset_choices()
                ),
                gr.update(
                    choices=get_asset_choices()
                ),
                gr.update(
                    choices=get_asset_choices()
                )
            )

    # 자산 삭제
    supabase \
        .table("assets") \
        .delete() \
        .eq(
            "name",
            asset_name
        ) \
        .execute()

    choices = get_asset_choices()

    value = (
        choices[0]
        if choices
        else None
    )

    return (
        f"🗑 '{asset_name}'이(가) 삭제되었습니다.",
        show_assets(),
        gr.update(
            choices=choices,
            value=value
        ),
        gr.update(
            choices=choices,
            value=value
        ),
        gr.update(
            choices=choices,
            value=value
        )
    )


# ============================================================
# 월별 통계
# ============================================================

def get_statistics(
    selected
):

    transactions = get_transaction_data()

    if not transactions:

        return (
            "아직 거래내역이 없습니다.",
            None
        )

    # 전체
    if selected == "전체":

        filtered_transactions = transactions
        title = "전체 통계"

    # 특정 월
    else:

        year = int(
            selected[:4]
        )

        month = int(
            selected[6:-1]
        )

        filtered_transactions = []

        for trans in transactions:

            date = dt.date.fromisoformat(
                trans["date"]
            )

            if (
                date.year == year
                and date.month == month
            ):

                filtered_transactions.append(
                    trans
                )

        title = selected

    total_income = 0
    total_expense = 0

    expense_category = {}

    # 수입 / 지출 계산
    for trans in filtered_transactions:

        amount = int(
            trans["amount"]
        )

        if trans["kind"] == "수입":

            total_income += amount

        else:

            total_expense += amount

            category = trans["category"]

            if category not in expense_category:

                expense_category[category] = 0

            expense_category[category] += amount

    variation = (
        total_income
        - total_expense
    )

    result = ""

    result += (
        f"===== {title} =====\n\n"
    )

    result += (
        f"총 수입 : "
        f"{total_income:,}원\n"
    )

    result += (
        f"총 지출 : "
        f"{total_expense:,}원\n"
    )

    result += (
        "-----------------------------\n"
    )

    result += (
        f"순증감 : "
        f"{variation:,}원\n"
    )

    # 지출 내역
    result += "\n[지출 내역]\n"

    if expense_category:

        for category, amount in expense_category.items():

            result += (
                f"{category} : "
                f"{amount:,}원\n"
            )

    else:

        result += (
            "지출 내역이 없습니다.\n"
        )

    # 가장 많이 쓴 항목
    result += "\n[가장 많이 쓴 항목]\n"

    if expense_category:

        max_category = max(
            expense_category,
            key=expense_category.get
        )

        result += (
            f"{max_category} : "
            f"{expense_category[max_category]:,}원\n"
        )

    else:

        result += (
            "지출 내역이 없습니다.\n"
        )

    # 지출 비율
    result += "\n[지출 비율]\n"

    if total_expense > 0:

        for category, amount in expense_category.items():

            ratio = (
                amount
                / total_expense
                * 100
            )

            result += (
                f"{category} : "
                f"{ratio:.1f}%\n"
            )

    else:

        result += (
            "지출 내역이 없습니다.\n"
        )

    # 그래프
    if expense_category:

        categories = list(
            expense_category.keys()
        )

        amounts = list(
            expense_category.values()
        )

        fig, ax = plt.subplots(
            figsize=(9, 5)
        )

        bars = ax.barh(
            categories,
            amounts,
            color="#FF8EA0"
        )

        ax.set_xlabel(
            "금액 (원)"
        )

        ax.set_ylabel(
            f"{title} 지출 내역"
        )

        max_amount = max(
            amounts
        )

        ax.set_xlim(
            0,
            max_amount * 1.25
        )

        for bar, amount in zip(
            bars,
            amounts
        ):

            ax.text(
                bar.get_width()
                + max_amount * 0.02,

                bar.get_y()
                + bar.get_height() / 2,

                f"{amount:,}원",

                va="center"
            )

        ax.grid(
            axis="x",
            linestyle="--",
            alpha=0.3
        )

        ax.spines[
            "top"
        ].set_visible(False)

        ax.spines[
            "right"
        ].set_visible(False)

        plt.tight_layout()

    else:

        fig = None

    return (
        result,
        fig
    )


# ============================================================
# GUI
# ============================================================

with gr.Blocks(
    title="곧감 가계부"
) as app:

    # 제목
    gr.Markdown(
        """
        # 🐻 곧감 가계부

        ### 곧감니다요 가계부
        """
    )

    # 현재 총 자산
    gr.Markdown(
        "## 💰 현재 자산"
    )

    total_asset = gr.Textbox(
        label="총 자산",
        value=f"{get_total_asset():,}원",
        interactive=False
    )

    # 자산 현황
    gr.Markdown(
        "### 💳 자산 현황"
    )

    asset_view = gr.Textbox(
        label="",
        value=show_assets(),
        lines=6,
        interactive=False
    )

    # 자산 관리
    gr.Markdown("---")

    gr.Markdown(
        "## 🏦 자산 관리"
    )

    # 자산 추가
    gr.Markdown(
        "### ➕ 자산 추가"
    )

    with gr.Row():

        new_asset_name = gr.Textbox(
            label="자산 이름",
            placeholder="예: 국민은행"
        )

        new_asset_money = gr.Number(
            label="초기 금액",
            value=0
        )

    add_asset_button = gr.Button(
        "➕ 자산 추가"
    )

    asset_message = gr.Textbox(
        label="",
        interactive=False
    )

    # 자산 이름 변경
    gr.Markdown(
        "### ✏️ 자산 이름 변경"
    )

    with gr.Row():

        rename_old = gr.Dropdown(
            choices=get_asset_choices(),
            label="현재 이름"
        )

        rename_new = gr.Textbox(
            label="새 이름",
            placeholder="예: BNK 부산은행"
        )

    rename_button = gr.Button(
        "✏️ 이름 변경"
    )

    # 자산 삭제
    gr.Markdown(
        "### 🗑️ 자산 삭제"
    )

    delete_asset_select = gr.Dropdown(
        choices=get_asset_choices(),
        label="삭제할 자산"
    )

    delete_asset_button = gr.Button(
        "🗑️ 자산 삭제"
    )

    # 거래 입력
    gr.Markdown("---")

    gr.Markdown(
        "## 💳 거래 입력"
    )

    with gr.Row():

        kind = gr.Radio(
            ["수입", "지출"],
            label="구분",
            value="지출"
        )

        category = gr.Textbox(
            label="분류",
            placeholder="예: 식비, 용돈, 교통비"
        )

    asset = gr.Dropdown(
        choices=get_asset_choices(),
        label="자산 종류",
        value=(
            get_asset_choices()[0]
            if get_asset_choices()
            else None
        )
    )

    amount = gr.Number(
        label="금액",
        minimum=1
    )

    save_button = gr.Button(
        "💾 거래 저장",
        variant="primary"
    )

    message = gr.Textbox(
        label="",
        interactive=False
    )

    # 거래 내역
    gr.Markdown(
        "## 📋 거래내역"
    )

    transaction_tabel = gr.Dataframe(
        value=get_transactions(),
        headers=[
            "번호",
            "날짜",
            "구분",
            "분류",
            "자산 종류",
            "금액"
        ],
        interactive=False
    )

    # 거래 삭제
    gr.Markdown(
        "### 🗑️ 거래 삭제"
    )

    delete_transaction_select = gr.Dropdown(
        choices=get_transaction_choices(),
        label="삭제할 거래"
    )

    delete_transaction_button = gr.Button(
        "🗑️ 선택한 거래 삭제"
    )

    delete_message = gr.Textbox(
        label="",
        interactive=False
    )

    # 월별 통계
    gr.Markdown("---")

    gr.Markdown(
        "## 📊 월별 통계"
    )

    with gr.Row():

        month_select = gr.Dropdown(
            choices=get_month_choices(),
            value="전체",
            label="확인할 기간"
        )

        stat_button = gr.Button(
            "📊 통계 보기",
            variant="primary"
        )

    statistics = gr.Textbox(
        label="통계 결과",
        lines=15,
        interactive=False
    )

    graph = gr.Plot(
        label="지출 그래프"
    )

    # 거래 저장 버튼
    save_button.click(
        add_transaction,

        inputs=[
            kind,
            category,
            asset,
            amount
        ],

        outputs=[
            message,
            total_asset,
            asset_view,
            transaction_tabel,
            delete_transaction_select,
            month_select
        ]
    )

    # 거래 삭제 버튼
    delete_transaction_button.click(
        delete_transaction,

        inputs=[
            delete_transaction_select
        ],

        outputs=[
            delete_message,
            total_asset,
            asset_view,
            transaction_tabel,
            delete_transaction_select,
            month_select
        ]
    )

    # 자산 추가 버튼
    add_asset_button.click(
        add_asset,

        inputs=[
            new_asset_name,
            new_asset_money
        ],

        outputs=[
            asset_message,
            total_asset,
            asset_view,
            asset,
            rename_old,
            delete_asset_select
        ]
    )

    # 자산 이름 변경 버튼
    rename_button.click(
        rename_asset,

        inputs=[
            rename_old,
            rename_new
        ],

        outputs=[
            asset_message,
            asset_view,
            asset,
            rename_old,
            delete_asset_select
        ]
    )

    # 자산 삭제 버튼
    delete_asset_button.click(
        delete_asset,

        inputs=[
            delete_asset_select
        ],

        outputs=[
            asset_message,
            asset_view,
            asset,
            rename_old,
            delete_asset_select
        ]
    )

    # 통계 버튼
    stat_button.click(
        get_statistics,

        inputs=[
            month_select
        ],

        outputs=[
            statistics,
            graph
        ]
    )


# ============================================================
# 실행
# ============================================================

port = int(
    os.getenv(
        "PORT",
        "7860"
    )
)

app.launch(
    server_name="0.0.0.0",
    server_port=port,
    share=False
)
