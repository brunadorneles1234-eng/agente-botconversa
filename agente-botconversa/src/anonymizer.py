import hashlib
import copy

_PERSONAL_FIELDS = {"contact_phone", "contact_name", "contact_email", "contact_cpf"}
_MESSAGE_CONTENT_FIELDS = {"text", "content", "body"}
_SALT = "botconv_lgpd"


def anonymize_conversation(conv: dict) -> dict:
    result = copy.deepcopy(conv)

    for field in _PERSONAL_FIELDS:
        result.pop(field, None)

    raw_id = str(conv.get("id", ""))
    hash_hex = hashlib.sha256(f"{_SALT}:{raw_id}".encode()).hexdigest()[:12]
    result["anon_id"] = f"conv_{hash_hex}"
    result.pop("id", None)

    if "messages" in result:
        cleaned = []
        for msg in result["messages"]:
            clean_msg = {k: v for k, v in msg.items() if k not in _MESSAGE_CONTENT_FIELDS}
            cleaned.append(clean_msg)
        result["messages"] = cleaned

    return result
