import PyPDF2
import pandas as pd
import re


def extract_text_from_pdf(pdf_file):
    """Extract text from each page of a PDF file."""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text_lines = []

    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text = page.extract_text()

        # Split the text into lines and clean them
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                text_lines.append(line)

    return text_lines


def save_to_csv(text_lines, output_file):
    """Save the extracted text lines to a CSV file."""

    df = pd.DataFrame(text_lines, columns=['texts'])


    df.to_csv(output_file, index=False)
    print(f"CSV file has been created with {len(text_lines)} lines of text.")


def main():

    pdf_file = 'C:/Users/Dipeolu Ayomide/PycharmProjects/Raterx/klinchainx/next_batch_for_may.pdf'


    output_file = 'output.csv'


    text_lines = extract_text_from_pdf(pdf_file)


    save_to_csv(text_lines, output_file)


if __name__ == "__main__":
    main()