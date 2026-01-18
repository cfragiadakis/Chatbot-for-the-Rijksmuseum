from pathlib import Path
from lxml import etree
from config import output_letters_van_gogh_path_eng, output_letters_van_gogh_path_nl, input_letters_van_gogh
from loguru import logger

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}

def extract_tei_div_text(xml_path: str, div_type: str = "original", drop_notes: bool = True) -> str:
    root = etree.parse(xml_path).getroot()

    # Select the div you want (often original/translation)
    divs = root.xpath(f'.//tei:body//tei:div[@type="{div_type}"]', namespaces=NS)
    if not divs:
        raise ValueError(f"No TEI div[@type='{div_type}'] found in {xml_path}")
    div = divs[0]

    # Optionally remove notes (so they don't appear in extracted text)
    if drop_notes:
        for note in div.xpath(".//tei:note", namespaces=NS):
            note.getparent().remove(note)

    # Convert TEI line breaks (<lb/>) into actual newlines
    for lb in div.xpath(".//tei:lb", namespaces=NS):
        lb.tail = ("\n" + (lb.tail or ""))

    # Get plain text
    text = " ".join(div.itertext())
    # Clean up whitespace a bit
    text = "\n".join(line.strip() for line in text.splitlines())
    text = "\n".join(line for line in text.split("\n") if line.strip())
    return text.strip()


if __name__ == "__main__":
    INPUT_DIR = Path(input_letters_van_gogh)
    logger.info("== Welcome to Jason's very own Van Gogh's letter parser! == \n")
    choice = input("Do you want the original letters (1) or the translation (2)? \n")
    if choice == "1":
        OUTPUT_DIR = Path(output_letters_van_gogh_path_nl) 
        OUTPUT_DIR.mkdir(exist_ok=True)
        div_type = "original"
        for xml_file in INPUT_DIR.glob("*.xml"):
            try:
                text = extract_tei_div_text(xml_file, div_type, drop_notes=True)
                (OUTPUT_DIR / (xml_file.stem + ".txt")).write_text(text, encoding="utf-8")
                logger.info("OK:", xml_file.name)
            except Exception as e:
                logger.warning("FAIL:", xml_file.name, "-", e)
    elif choice == "2":
        OUTPUT_DIR = Path(output_letters_van_gogh_path_eng)
        OUTPUT_DIR.mkdir(exist_ok=True)
        div_type = "translation"
        for xml_file in INPUT_DIR.glob("*.xml"):
            try:
                text = extract_tei_div_text(xml_file, div_type, drop_notes=True)
                (OUTPUT_DIR / (xml_file.stem + ".txt")).write_text(text, encoding="utf-8")
                logger.info("OK:", xml_file.name)
            except Exception as e:
                logger.warning("FAIL:", xml_file.name, "-", e)
    else:
        logger.warning("Invalid choice.")
        exit()




