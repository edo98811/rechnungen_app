from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from app.models.receipt import Receipt

CURRENCY_FORMAT = "#,##0.00"
HEADERS = ["Item", "Quantity", "Unit Price", "Total Price"]


def receipt_to_excel(receipt: Receipt) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Receipt"

    sheet.append(["Store", receipt.store_name])
    sheet.append(["Date", receipt.date])
    sheet.append([])

    sheet.append(HEADERS)
    for cell in sheet[sheet.max_row]:
        cell.font = Font(bold=True)

    for item in receipt.items:
        sheet.append([item.name, item.quantity, item.unit_price, item.total_price])
        sheet.cell(row=sheet.max_row, column=3).number_format = CURRENCY_FORMAT
        sheet.cell(row=sheet.max_row, column=4).number_format = CURRENCY_FORMAT

    sheet.append([])
    for label, value in [
        ("Subtotal", receipt.subtotal),
        ("Tax", receipt.tax_amount),
        ("Total", receipt.total),
    ]:
        sheet.append([label, "", "", value])
        sheet.cell(row=sheet.max_row, column=4).number_format = CURRENCY_FORMAT
        if label == "Total":
            for cell in sheet[sheet.max_row]:
                cell.font = Font(bold=True)

    for index, column_cells in enumerate(sheet.columns, start=1):
        lengths = [len(str(cell.value)) for cell in column_cells if cell.value not in (None, "")]
        width = max(lengths, default=8) + 2
        sheet.column_dimensions[get_column_letter(index)].width = width

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
