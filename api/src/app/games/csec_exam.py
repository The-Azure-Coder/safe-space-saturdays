"""Private, server-authoritative CSEC IT mock examination game."""

from __future__ import annotations

from typing import Any

from app.games.connect_four import IllegalMove

PAPER_ONE: tuple[dict[str, Any], ...] = (
    {
        "question": "Which component stores data and instructions currently being used by the CPU?",
        "options": ["ROM", "RAM", "Hard disk drive", "Optical disc"],
        "correct": 1,
    },
    {
        "question": "Which device reads shaded responses on a multiple-choice answer sheet?",
        "options": ["OCR", "OMR", "MICR", "Barcode reader"],
        "correct": 1,
    },
    {
        "question": "Which of these is system software?",
        "options": [
            "Spreadsheet package",
            "Operating system",
            "Presentation file",
            "Database table",
        ],
        "correct": 1,
    },
    {
        "question": "Which statement distinguishes data from information?",
        "options": [
            "Data is processed facts",
            "Data is raw facts while information is processed data with meaning",
            "Data is only numeric",
            "Data is stored locally",
        ],
        "correct": 1,
    },
    {
        "question": "A student's age must be between 11 and 20. Which validation check is appropriate?",
        "options": ["Presence check", "Range check", "Format check", "Length check"],
        "correct": 1,
    },
    {
        "question": "Which is a verification method?",
        "options": ["Type check", "Range check", "Double entry", "Presence check"],
        "correct": 2,
    },
    {
        "question": "Which device reads magnetic characters on bank cheques?",
        "options": ["MICR", "OMR", "OCR", "Touchscreen"],
        "correct": 0,
    },
    {
        "question": "Which two specifications should be prioritized for heavy video editing?",
        "options": [
            "High RAM and fast processor",
            "Low RAM and small SSD",
            "Large keyboard and slow processor",
            "Small storage and low-resolution display",
        ],
        "correct": 0,
    },
    {
        "question": "Which is an advantage of cloud storage?",
        "options": [
            "It never requires authentication",
            "Files can be accessed from multiple Internet-connected devices",
            "It always works offline",
            "It removes all security risks",
        ],
        "correct": 1,
    },
    {
        "question": "A payroll system processes records in employee-number order. Which access method fits best?",
        "options": ["Sequential access", "Random access", "Direct access", "Real-time access"],
        "correct": 0,
    },
    {
        "question": "A network within one school building is a",
        "options": ["LAN", "WAN", "MAN", "Extranet"],
        "correct": 0,
    },
    {
        "question": "Which device forwards data between different networks?",
        "options": ["Switch", "Router", "Scanner", "Monitor"],
        "correct": 1,
    },
    {
        "question": "Which device connects multiple devices within the same LAN?",
        "options": ["Switch", "Printer", "Plotter", "OMR reader"],
        "correct": 0,
    },
    {
        "question": "Which medium suits very high-speed communication over long cable distances?",
        "options": ["Fibre-optic cable", "Infrared", "Twisted-pair cable", "Bluetooth"],
        "correct": 0,
    },
    {
        "question": "Which technology suits a short-range connection between a phone and earbuds?",
        "options": ["Bluetooth", "Satellite", "Fibre optic", "Coaxial cable"],
        "correct": 0,
    },
    {
        "question": "What best describes the World Wide Web?",
        "options": [
            "Physical Internet cables",
            "Interlinked resources accessed using the Internet",
            "A company private network",
            "An operating system",
        ],
        "correct": 1,
    },
    {
        "question": "Which software requests, receives and displays web pages?",
        "options": ["Web browser", "Router", "Switch", "Modem"],
        "correct": 0,
    },
    {
        "question": "What is the main purpose of a URL?",
        "options": [
            "Identify the address of an online resource",
            "Connect computers in a LAN",
            "Encrypt every web page",
            "Store web pages permanently",
        ],
        "correct": 0,
    },
    {
        "question": "Sending a photograph from a laptop to a web server is",
        "options": ["Uploading", "Downloading", "Validating", "Formatting"],
        "correct": 0,
    },
    {
        "question": "Controlled supplier access to part of a private network is an",
        "options": ["Extranet", "Internet", "LAN", "Bluetooth network"],
        "correct": 0,
    },
    {
        "question": "A weakness in a computer system that can be exploited is a",
        "options": ["Threat", "Vulnerability", "Countermeasure", "Backup"],
        "correct": 1,
    },
    {
        "question": "An email asking for login details through a fake bank website is",
        "options": ["Phishing", "Compression", "Defragmentation", "Telemedicine"],
        "correct": 0,
    },
    {
        "question": "What makes stored or transmitted data unreadable without a key?",
        "options": ["Encryption", "Sorting", "Formatting", "Filtering"],
        "correct": 0,
    },
    {
        "question": "Which pair best reduces unauthorized account access?",
        "options": [
            "Strong unique passwords and multi-factor authentication",
            "Sharing passwords and disabling updates",
            "One password everywhere and no antivirus",
            "Unknown attachments and public Wi-Fi",
        ],
        "correct": 0,
    },
    {
        "question": "What best protects files after hardware failure or ransomware?",
        "options": [
            "Regular tested backups",
            "Increasing monitor brightness",
            "Sorting folders",
            "Changing wallpaper",
        ],
        "correct": 0,
    },
    {
        "question": "Which professional analyses requirements and recommends an information-system solution?",
        "options": ["Systems analyst", "Receptionist", "Graphic artist", "Data-entry clerk"],
        "correct": 0,
    },
    {
        "question": "Which is a likely effect of automation?",
        "options": [
            "Higher productivity but possible displacement of some workers",
            "Guaranteed employment",
            "No training needs",
            "Lower productivity everywhere",
        ],
        "correct": 0,
    },
    {
        "question": "Which is a positive impact of ICT on education?",
        "options": [
            "Distance learning can reach students in different locations",
            "It guarantees no plagiarism",
            "It prevents collaboration",
            "It removes evaluation of online information",
        ],
        "correct": 0,
    },
    {
        "question": "Which ICT application is closely associated with medicine?",
        "options": [
            "Telemedicine",
            "Electronic voting",
            "Computer-aided manufacturing",
            "Traffic-light control",
        ],
        "correct": 0,
    },
    {
        "question": "What is safest when an unexpected email asks for a password?",
        "options": [
            "Verify the sender and link independently",
            "Reply with the password",
            "Forward it to every contact",
            "Disable antivirus",
        ],
        "correct": 0,
    },
)

PAPER_TWO: tuple[dict[str, Any], ...] = (
    {
        "id": "1a",
        "prompt": "State FOUR major hardware components of a computer system.",
        "marks": 4,
    },
    {
        "id": "1b",
        "prompt": "Recommend TWO computer specifications for video editing and explain why EACH is important.",
        "marks": 4,
    },
    {
        "id": "1c",
        "prompt": "State TWO suitable validation checks for age, email address or telephone number and give an example of EACH.",
        "marks": 4,
    },
    {
        "id": "1d",
        "prompt": "State ONE verification method for information entered from a paper source and explain how it improves accuracy.",
        "marks": 2,
    },
    {
        "id": "1e",
        "prompt": "Name TWO network devices needed in the school network and describe the function of EACH.",
        "marks": 4,
    },
    {"id": "1f", "prompt": "Distinguish between a LAN and a WAN.", "marks": 2},
    {
        "id": "1g",
        "prompt": "Explain the role of a web browser and a URL when a student accesses the school's website.",
        "marks": 3,
    },
    {
        "id": "2a",
        "prompt": "Identify the type of computer misuse described in the clinic phishing scenario.",
        "marks": 1,
    },
    {
        "id": "2b",
        "prompt": "Using the clinic scenario, explain vulnerability, threat and attack.",
        "marks": 6,
    },
    {
        "id": "2c",
        "prompt": "Explain TWO possible effects of the misuse on the clinic or its patients.",
        "marks": 4,
    },
    {
        "id": "2d",
        "prompt": "Recommend THREE security countermeasures and explain how EACH reduces risk or impact.",
        "marks": 6,
    },
    {
        "id": "2e",
        "prompt": "State ONE positive and ONE negative impact of ICT on medicine.",
        "marks": 2,
    },
    {
        "id": "2f",
        "prompt": "Explain automation's effect on productivity and job security using ONE workplace example.",
        "marks": 2,
    },
    {
        "id": "2g",
        "prompt": "Name ONE IT professional who could protect or maintain the clinic's information systems.",
        "marks": 1,
    },
)


def new_csec_exam_state(player_count: int = 2) -> dict[str, Any]:
    count = max(1, min(2, player_count))
    return {
        "game": "csec-it-mock-exam",
        "phase": "paper_one",
        "question_index": 0,
        "paper_one": [dict(question=q["question"], options=q["options"]) for q in PAPER_ONE],
        "paper_two": [dict(id=q["id"], prompt=q["prompt"], marks=q["marks"]) for q in PAPER_TWO],
        "answers_one": [[None] * len(PAPER_ONE) for _ in range(count)],
        "answers_two": [["" for _ in PAPER_TWO] for _ in range(count)],
        "paper_one_scores": [0] * count,
        "paper_two_scores": [0] * count,
        "grades": [[None for _ in PAPER_TWO] for _ in range(count)],
        "player_count": count,
        "players": [
            {"name": "You" if i == 0 else "Kashi Miller", "is_bot": False} for i in range(count)
        ],
        "winner": None,
        "draw": False,
    }


def apply_csec_exam_action(
    state: dict[str, Any], player: int, payload: dict[str, Any]
) -> dict[str, Any]:
    if player < 0 or player >= int(state["player_count"]):
        raise IllegalMove("You are not seated in this exam")
    action = payload.get("action")
    if action == "answer_one":
        index = int(payload.get("question_index", -1))
        answer = int(payload.get("answer", -1))
        if index not in range(len(PAPER_ONE)) or answer not in range(4):
            raise IllegalMove("Choose one of the four answers")
        state["answers_one"][player][index] = answer
        state["question_index"] = min(len(PAPER_ONE) - 1, index + 1)
        if all(value is not None for value in state["answers_one"][player]):
            state["paper_one_scores"][player] = sum(
                value == question["correct"]
                for value, question in zip(state["answers_one"][player], PAPER_ONE, strict=True)
            )
            state["phase"] = "paper_two"
        return state
    if action == "answer_two":
        item = str(payload.get("question_id", ""))
        answer = str(payload.get("answer", ""))[:5000]
        index = next((i for i, q in enumerate(PAPER_TWO) if q["id"] == item), -1)
        if index < 0:
            raise IllegalMove("That structured question does not exist")
        state["answers_two"][player][index] = answer
        return state
    if action == "submit_exam":
        if any(value is None for value in state["answers_one"][player]):
            raise IllegalMove("Answer every Paper 1 question first")
        state["phase"] = "complete"
        state["winner"] = None
        return state
    if action == "grade_two":
        if state["players"][player].get("name", "").strip().casefold() != "tyrese":
            raise IllegalMove("Only Tyrese can grade this private exam")
        target = int(payload.get("target_player", 0))
        item = str(payload.get("question_id", ""))
        points = int(payload.get("points", 0))
        index = next((i for i, q in enumerate(PAPER_TWO) if q["id"] == item), -1)
        if (
            target not in range(int(state["player_count"]))
            or index < 0
            or points not in range(PAPER_TWO[index]["marks"] + 1)
        ):
            raise IllegalMove("Grade must be within the question's mark range")
        state["grades"][target][index] = {
            "points": points,
            "feedback": str(payload.get("feedback", ""))[:1000],
        }
        state["paper_two_scores"][target] = sum(
            (grade or {}).get("points", 0) for grade in state["grades"][target]
        )
        return state
    raise IllegalMove("That exam action is not available")
