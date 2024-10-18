from io import BytesIO
from zipfile import ZipFile

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from rest_framework.renderers import BaseRenderer


class ExcelRenderer(BaseRenderer):
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    format = "xlsx"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Check if the data is in the correct format for rendering
        if not isinstance(data, dict) or "data" not in data:
            return None

        # Create an in-memory output stream for the Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for data_type, data_list in data["data"].items():
                print(data_list)
                df = pd.DataFrame(data=data_list)
                df.columns = [col.title() for col in df.columns]
                df.to_excel(writer, sheet_name=data_type.title(), index=False)

        output.seek(0)  # Reset the stream's position to the beginning

        # Return the output stream as the response
        return output.read()



class CsvRenderer(BaseRenderer):
    media_type = "application/zip"
    format = "csv"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if not isinstance(data, dict) or "data" not in data:
            return None

        # Create an in-memory buffer to store the zip file
        zip_buffer = BytesIO()

        # Create a ZipFile object
        with ZipFile(zip_buffer, 'w') as zip_file:
            # Iterate through each dataset and generate a separate CSV file for each
            for data_type, data_list in data["data"].items():
                if not data_list:
                    continue

                # Convert data to DataFrame
                df = pd.DataFrame(data=data_list)
                df.columns = [col.title() for col in df.columns]  # Title case the column names

                # Create a BytesIO buffer for each CSV file
                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, sep=",", index=False)
                csv_buffer.seek(0)

                # Write the CSV buffer to the ZIP file
                csv_filename = f"{data_type.lower().replace(' ', '_')}.csv"
                zip_file.writestr(csv_filename, csv_buffer.read())

        # Reset the stream position of the zip buffer
        zip_buffer.seek(0)

        # Return the binary content of the ZIP file
        return zip_buffer.read()




class PdfRenderer(BaseRenderer):
    media_type = "application/pdf"
    format = "pdf"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Validate input data
        if not isinstance(data, dict) or "data" not in data or not data.get("data"):
            return b""  # Return empty byte string if data is invalid

        # Extract 'people' data from the input JSON data

        # Create an in-memory output stream for the PDF
        output = BytesIO()
       

        # Setup PDF document
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=18,
            title="Data Report" 
        )
        document.pagesize = landscape(A4)
        
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        normal_style = styles["BodyText"]
        styles.wordWrap = "CJK"

        # page_width, _ = A4
        # table_margin = 72  # 1 inch margin (in points)

        # Create PDF elements
        elements = [Spacer(1, 0.25 * inch)]
        for key, val in data["data"].items():
            if not isinstance(val, list) or not val:
                continue

            # Prepare data for the table with headers
            elements.append(Paragraph(f"{key.title()} Data", title_style))
            elements.append(Spacer(1, 0.15 * inch))

            # Extract headers dynamically based on the first item's keys
            headers = (
                [header.title().replace("_", " ") for header in val[0].keys()]
                if val
                else []
            )
            table_data = [headers]

            for item in val:
                row = [
                    Paragraph(str(item.get(header.lower().replace(" ", "_"), "")), normal_style)
                    for header in headers
                ]
                table_data.append(row)
                
            table = Table(table_data)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            # Add table to elements
            elements.append(table)
            elements.append(Spacer(1, 0.25 * inch))
            elements.append(PageBreak())

        # Build PDF in the output stream
        document.build(elements)
        output.seek(0)  # Reset the stream's position to the beginnin
        return output.getvalue()


