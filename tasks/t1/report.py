import sys


def main(argv):
    if len(argv) < 2:
        print("usage: report.py <csv>")
        return 1
    print(f"read {argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
