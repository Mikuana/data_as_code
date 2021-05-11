from hashlib import md5
from uuid import uuid4
from pathlib import Path

from data_as_code import Recipe, Step, ingredient, result
from data_as_code.misc import INTERMEDIARY, SOURCE, PRODUCT


# def test_pickup(tmpdir):
#     class R(Recipe):
#         trust_cache = True
#
#         class Step1(Step):
#             """ non-deterministic """
#             output = result('file1')
#             keep = True
#
#             def instructions(self):
#                 self.output.write_text(
#                     uuid4().hex
#                 )
#
#         class Step2(Step):
#             """ non-deterministic, affected by Step1 input """
#             output = result('file2')
#             x = ingredient('Step1')
#
#             def instructions(self):
#                 self.output.write_text(
#                     md5(self.x.read_bytes()).hexdigest() + uuid4().hex
#                 )
#
#         class Step3(Step):
#             """ deterministic, affected by step 2 input """
#             output = result('file3')
#             x = ingredient('Step2')
#             keep = True
#
#             def instructions(self):
#                 self.output.write_text(
#                     md5(self.x.read_bytes()).hexdigest()
#                 )
#
#         class Step4(Step):
#             """ Combine results of Step1 and Step 3 """
#             x = ingredient('Step1')
#             y = ingredient('Step3')
#             output = result('file4')
#
#             def instructions(self):
#                 txt = self.x.read_text() + self.y.read_text()
#                 self.output.write_text(txt)
#
#     R(tmpdir).execute()
#     p1 = Path(tmpdir, 'data', 'file1')
#     p3 = Path(tmpdir, 'data', 'file3')
#     p4 = Path(tmpdir, 'data', 'file4')
#     # file4 is a result of file1 and file3
#     assert p4.read_text() == (p1.read_text() + p3.read_text())
#
#     p4.unlink()  # pickup should recreate file4 from cached file1 and file3
#     R(tmpdir, pickup=True).execute()
#     assert p4.read_text() == (p1.read_text() + p3.read_text())
#     # TODO: schema error is being introduced in pickup process by nested lineage
#     #  which ends up with an empty derived metadata node for Step2
