from pathlib import Path
from uuid import uuid4

from data_as_code import Recipe, Step, ingredient, result, Role


def test_pickup(tmpdir):
    """
    Complex pickup testing

    This test runs a Recipe four Steps to determine if Step pickup is
    functioning the way that it is intended.

      - Steps 1, 2, and 3 generate random content
      - Step4 combines content of Step1 and Step3

    In the first execution of the recipe, all four steps should execute
    sequentially. After execution, we assert that the content of Step4 is the
    combination of Step1 and Step3. Then, we remove Step4.

    The environment is now set up for testing of a pickup using a second
    execution of the Recipe. Because Steps 1, 2, and 3 are random, and Step4 is
    derived from the randomness of Step 1 and Step 2, if the execution doesn't
    use the cache then it will cause the content of Step4 to differ between
    executions (which we do not want).

    We expect that the pickup execution will do the following:

      1. Identify Step4 as a product, indicating that is must be executed
      2. Determine that the artifacts for Step4 are missing (i.e. there's no
         data file), and that the cache cannot be used for Step4
      3. Determine that Step1 and Step3 must be executed in order to support the
         execution of Step4
      4. Determine that Step1 and Step3 have valid artifacts in the cache, and
         use those in the execution of instructions for Step4
      5. Execute Step4 and output another file, which is identical to the file
         output by Step4 in the first execution.

    In order to pass the pickup execution, the Recipe cannot use the cache for
    Step4, but it must use it for Steps 1 and 3. Step 2 should not be executed,
    as it is not an ingredient of Step4.
    """

    class R(Recipe):
        trust_cache = True
        keep = list(Role)

        class Step1(Step):
            output = result('file1')

            def instructions(self):
                self.output.write_text(uuid4().hex)

        class Step2(Step1):
            x = ingredient('Step1')
            keep = False

        class Step3(Step1):
            output = result('file3')
            x = ingredient('Step2')

        class Step4(Step):
            x = ingredient('Step1')
            y = ingredient('Step3')
            output = result('file4')

            def instructions(self):
                self.output.write_text(self.x.read_text() + self.y.read_text())

    R(tmpdir).execute()
    p1 = Path(tmpdir, 'data', 'file1')
    p3 = Path(tmpdir, 'data', 'file3')
    p4 = Path(tmpdir, 'data', 'file4')

    initial = p4.read_text()
    assert initial == (p1.read_text() + p3.read_text())

    p4.unlink()
    R(tmpdir, pickup=True).execute()
    pickup = p4.read_text()
    assert initial == pickup
