import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

def sanitize_text(text: str) -> str:
    return text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n").strip()
