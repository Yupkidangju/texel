from .editing import apply_borders, format_range, merge_range, set_matrix
from .model import Workbook


def demo_workbook():
    book = Workbook()
    book.sheet().name = "매출"
    set_matrix(
        book,
        0,
        "A1",
        [
            ["부서", "지역", "월", "매출", "비용", "이익", "이익률"],
            ["영업", "서울", "1", "120000", "40000", "=D2-E2", "=IFERROR(F2/D2,0)"],
            ["개발", "부산", "1", "90000", "50000", "=D3-E3", "=IFERROR(F3/D3,0)"],
            ["영업", "서울", "2", "155000", "65000", "=D4-E4", "=IFERROR(F4/D4,0)"],
            ["지원", "대전", "1", "60000", "28000", "=D5-E5", "=IFERROR(F5/D5,0)"],
            ["개발", "부산", "2", "110000", "57000", "=D6-E6", "=IFERROR(F6/D6,0)"],
            ["지원", "대전", "2", "75000", "32000", "=D7-E7", "=IFERROR(F7/D7,0)"],
            ["합계", "", "", "=SUM(D2:D7)", "=SUM(E2:E7)", "=SUM(F2:F7)", "=IFERROR(F8/D8,0)"],
        ],
    )
    format_range(book, 0, "A1:G1", bold=True, background="#164e63", foreground="#ecfeff")
    format_range(book, 0, "D2:F8", number_format="number", decimals=0)
    format_range(book, 0, "G2:G8", number_format="percent", decimals=1)
    format_range(book, 0, "A8:G8", bold=True)
    book.sheet().freeze_rows = 1
    book.sheet().column_widths = {0: 12, 1: 12, 2: 8, 3: 16, 4: 16, 5: 16, 6: 14}
    book.sheet().cell(
        0, 0
    ).note = "데이터 메뉴에서 정렬/필터, 분석 메뉴에서 프로파일/피벗/차트를 실행하세요."
    book.named_ranges["Revenue"] = ("매출", "D2:D7")
    book.add_sheet("요약")
    set_matrix(
        book,
        1,
        "A1",
        [
            ["지표", "값"],
            ["총 매출", "=SUM(Revenue)"],
            ["평균 매출", "=AVERAGE(Revenue)"],
            ["총 이익", "=SUM('매출'!F2:F7)"],
            ["중앙값", "=MEDIAN(Revenue)"],
        ],
    )
    format_range(book, 1, "A1:B1", bold=True, background="#164e63", foreground="#ecfeff")
    format_range(book, 1, "B2:B5", number_format="number", decimals=0)
    book.sheet(1).column_widths = {0: 18, 1: 20}
    sheet = book.add_sheet("서식 예제")
    set_matrix(book, sheet, "A1", [["병합 · 테두리 · 줄바꿈"]])
    merge_range(book, sheet, "A1:E2")
    format_range(
        book,
        sheet,
        "A1:E2",
        bold=True,
        align="center",
        vertical_align="middle",
        background="#164e63",
        foreground="#ecfeff",
    )
    apply_borders(book, sheet, "A1:E2", "outer", "thick", "#2dd4bf")
    set_matrix(book, sheet, "A4", [["얇은 선", "중간 선", "굵은 선", "이중 선", "점선"]])
    for c, style in enumerate(("thin", "medium", "thick", "double", "dotted")):
        apply_borders(book, sheet, f"{chr(65 + c)}4", "all", style, "#94a3b8")
    set_matrix(
        book,
        sheet,
        "A6",
        [["우클릭해서 셀 서식과 테두리를 바꿔 보세요.\n병합 셀도 복사, 이동, 분할할 수 있습니다."]],
    )
    merge_range(book, sheet, "A6:E8")
    format_range(book, sheet, "A6:E8", wrap=True, vertical_align="middle", align="center")
    apply_borders(book, sheet, "A6:E8", "outer", "double", "#38bdf8")
    book.sheet(sheet).row_heights[5] = 2
    book.sheet(sheet).column_widths = {c: 16 for c in range(5)}
    sheet = book.add_sheet("업무 함수")
    set_matrix(
        book,
        sheet,
        "A1",
        [
            ["부서", "수량", "단가", "매출"],
            ["개발", "2", "1500", "=B2*C2"],
            ["영업", "3", "2000", "=B3*C3"],
            ["개발", "4", "1200", "=B4*C4"],
            ["영업", "1", "1000", "=B5*C5"],
        ],
    )
    set_matrix(
        book,
        sheet,
        "F1",
        [
            ["기능", "계산 결과"],
            ["개발 평균 매출", '=AVERAGEIF(A2:A5,"개발",D2:D5)'],
            ["영업 최고 매출", '=MAXIFS(D2:D5,A2:A5,"영업")'],
            ["수량 × 단가 합계", "=SUMPRODUCT(B2:B5,C2:C5)"],
            ["다음 업무일", "=WORKDAY(DATE(2026,10,16),1)"],
            ["월말", "=EOMONTH(DATE(2026,10,15),0)"],
            ["없는 항목 복구", '=IFNA(MATCH("미등록",A2:A5,0),"없음")'],
        ],
    )
    format_range(book, sheet, "A1:G1", bold=True, background="#164e63", foreground="#ecfeff")
    book.sheet(sheet).freeze_rows = 1
    book.sheet(sheet).column_widths = {0: 12, 1: 8, 2: 10, 3: 12, 4: 4, 5: 22, 6: 20}
    book.sheet(sheet).cell(
        0, 0
    ).note = "데이터 메뉴의 다중 열 정렬/복합 필터와 도움말의 수식 참조 진단을 사용해 보세요."
    return book
