def _clean_tag(tag):
    # Assume some logic that processes the tag
    return tag.strip().lower()


def _escape_control_tokens(input_string):
    control_tokens = ["\n", "\t", "\r"]
    for token in control_tokens:
        input_string = input_string.replace(token, "")
    return input_string
