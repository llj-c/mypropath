import pytest
def main():
    pytest.main(["-v", "--run-id", "11215211221sasa", "tests/testnewlogger.py"])

if __name__ == "__main__":
    main()