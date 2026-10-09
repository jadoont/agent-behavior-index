def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def mean(values):
    return sum(values) / len(values)
