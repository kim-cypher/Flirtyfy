"""
Generates rep3 and rep4 for each conversation in Mysamples.md
by calling the left-panel API twice per conversation.
Appends results to the file.
"""
import re
import time
import random
import requests

AUTH_TOKEN = '5dc132d7c87f6b005e41f024145afc63633e1321'
API_URL = 'http://localhost:8000/api/chat/generate-specific/'
SAMPLES_FILE = r'C:\Users\kiman\Projects\Flirtyfy\Mysamples.md'

HEADERS = {
    'Authorization': f'Token {AUTH_TOKEN}',
    'Content-Type': 'application/json',
}


def call_api(conversation_text: str) -> str:
    try:
        resp = requests.post(
            API_URL,
            json={'conversation': conversation_text},
            headers=HEADERS,
            timeout=45,
        )
        data = resp.json()
        if data.get('success'):
            return data['response']
        return f"ERROR: {data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"ERROR: {e}"


def parse_conversations(text: str):
    """
    Returns list of (header, conversation_text) tuples.
    Stops at the BUTTONS section.
    """
    # Trim at the BUTTONS divider
    buttons_idx = text.find('BUTTONS___')
    body = text[:buttons_idx] if buttons_idx != -1 else text

    # Split on the rep markers to find conversation blocks
    # Each block: [header line(s)] + [conversation lines] then ends at "rep 1:" or "rep1:"
    # Strategy: find all rep1 positions, work backwards to find the block start
    rep1_re = re.compile(r'\n+[ \t]*rep\s*1\s*:', re.IGNORECASE)
    rep_positions = [m.start() for m in rep1_re.finditer(body)]

    # Also find header lines (numbered ordinals / word ordinals)
    # We'll use rep boundaries to delimit the end of each conversation text
    # and look for the previous header to label it
    header_re = re.compile(
        r'^[ \t]*(FIRST|SECOND|THIRD|\d{1,2}(?:ST|ND|RD|TH))[ \t]*$',
        re.IGNORECASE | re.MULTILINE,
    )
    headers = list(header_re.finditer(body))

    conversations = []
    for i, hm in enumerate(headers):
        h_start = hm.end()  # text starts after the header line
        # conversation text ends at the next rep1 marker AFTER this header
        conv_end = None
        for rpos in rep_positions:
            if rpos > h_start:
                conv_end = rpos
                break
        if conv_end is None:
            continue  # no rep1 found after this header — skip

        conv_text = body[h_start:conv_end].strip()
        # Clean up: remove blank lines between timestamp blocks but keep structure
        label = hm.group(1).strip().upper()
        conversations.append((label, conv_text))

    return conversations


def find_last_rep_end(file_content: str, conv_label: str) -> int:
    """
    Find the character position of the end of the last rep line
    for a specific conversation so we can append after it.
    Not needed for our append approach — we'll append everything at the end.
    """
    pass


def main():
    with open(SAMPLES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    conversations = parse_conversations(content)
    print(f"Found {len(conversations)} conversations to process.\n")

    results = []
    for idx, (label, conv_text) in enumerate(conversations, 1):
        if len(conv_text) < 20:
            print(f"[{idx:02d}/{len(conversations)}] {label}: SKIPPED (too short)")
            results.append((label, "SKIPPED", "SKIPPED"))
            continue

        print(f"[{idx:02d}/{len(conversations)}] {label}: calling API (rep3)...")
        rep3 = call_api(conv_text)
        time.sleep(0.8)  # avoid rate limiting

        print(f"[{idx:02d}/{len(conversations)}] {label}: calling API (rep4)...")
        rep4 = call_api(conv_text)
        time.sleep(0.8)

        results.append((label, rep3, rep4))
        print(f"  rep3: {rep3[:80]}...")
        print(f"  rep4: {rep4[:80]}...")
        print()

    # Build the append block
    lines = ['\n\n', '# Rep3 & Rep4 — Post-Fix Test (June 19, 2026)', '\n']
    for label, rep3, rep4 in results:
        lines.append(f'\n## {label}')
        lines.append(f'\nrep3: {rep3}')
        lines.append(f'\nrep4: {rep4}')
        lines.append('\n')

    append_text = '\n'.join(lines)

    with open(SAMPLES_FILE, 'a', encoding='utf-8') as f:
        f.write(append_text)

    print(f"\nDone. Appended rep3 & rep4 for {len(results)} conversations to {SAMPLES_FILE}")


if __name__ == '__main__':
    main()
