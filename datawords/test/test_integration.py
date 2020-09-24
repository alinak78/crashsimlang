import os
from runner import main as runner_main
from cslang import main as cslang_main


class TestIntegration():

  def teardown(self):
    os.system("rm test/*.dw")
    os.system("rm test/*.pickle")
    os.system("rm test/*.auto")

  def test_openclose(self):
    test_file = "test/openclose.cslang"
    cslang_main(test_file)
    automaton = runner_main(test_file)
    assert automaton.current_state == 3
    assert automaton.is_accepting
    assert automaton.registers["filedesc"] == "3"
    assert automaton.registers["filename"] == "test.txt"
    assert automaton.registers["retval"] == "-1"

