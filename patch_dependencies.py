import re

# ------------- E-Mail Searcher -------------
with open('tests/unit/test_email_searcher.py') as f:
    email_content = f.read()

email_new_patches = """        patch("Core.Support.DateFormat.Get.Format", return_value="%Y-%m-%d"),
        patch("Core.Support.ApiCheck.Check.WhoIs", return_value="FAKE_API_KEY"),
"""
if 'patch("Core.Support.DateFormat.Get.Format"' not in email_content:
    email_content = email_content.replace(
        'patch("Core.Support.Banner_Selector.Random.Get_Banner", return_value=None),',
        'patch("Core.Support.Banner_Selector.Random.Get_Banner", return_value=None),\n' + email_new_patches
    )

with open('tests/unit/test_email_searcher.py', 'w') as f:
    f.write(email_content)


# ------------- Port Scanner -------------
with open('tests/unit/test_port_scanner.py') as f:
    port_content = f.read()

port_new_patches = """        patch("Core.Support.DateFormat.Get.Format", return_value="%Y-%m-%d"),
"""
if 'patch("Core.Support.DateFormat.Get.Format"' not in port_content:
    port_content = port_content.replace(
        'patch("Core.Support.Banner_Selector.Random.Get_Banner", return_value=None),',
        'patch("Core.Support.Banner_Selector.Random.Get_Banner", return_value=None),\n' + port_new_patches
    )

with open('tests/unit/test_port_scanner.py', 'w') as f:
    f.write(port_content)

print("Dependencies patched.")
