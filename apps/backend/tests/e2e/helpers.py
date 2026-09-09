


def sample_csv(*tokens: str) -> str:
    header = (
        "token,default_probability,payment_capacity,"
        "contract_propensity,filter_flag\n"
    )
    rows = [
        f"{token},0.15,5000,0.6,0\n" if i % 2 == 0 else f"{token},0.20,4000,0.4,0\n"
        for i, token in enumerate(tokens)
    ]
    return header + "".join(rows)
