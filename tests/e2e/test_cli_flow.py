import pexpect
import subprocess
import sys
import os
import pytest

# Test Environment Setup
# Đảm bảo chúng ta chạy các file test trong ngữ cảnh thư mục gốc của dự án.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MR_HOLMES_SCRIPT = os.path.join(PROJECT_ROOT, "MrHolmes.py")

def test_export_without_investigation_id_fails():
    """Test Non-Interactive Mode (Batch/Export): Missing params triggers correct failure and exits."""
    res = subprocess.run(
        [sys.executable, MR_HOLMES_SCRIPT, "--export", "csv"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    assert res.returncode == 1
    assert "--export requires --investigation" in res.stdout


def test_display_banner_and_exit():
    """Test Interactive Mode: App boots, shows banner, handles agreement optionally, then exits via Option 15."""
    child = pexpect.spawn(f"{sys.executable} {MR_HOLMES_SCRIPT}", cwd=PROJECT_ROOT, encoding='utf-8')
    
    # Ứng dụng có thể hỏi Agreement nếu đây là lần chạy đầu tiên
    idx = child.expect([r'\(Y/N\)', r'-->', pexpect.EOF], timeout=10)
    if idx == 0:
        child.sendline('y')
        child.expect(r'-->', timeout=10)
    elif idx == 2:
        pytest.fail("Process died unexpectedly early")

    # Chọn Option 15: Exit
    child.sendline('15')
    
    # Đợi thoát an toàn
    child.expect(pexpect.EOF, timeout=10)
    child.close()
    # Depending on how exit() is called, exitstatus can be 0 or None / string match.
    # Ở đây ta chỉ cần nó đóng mà không treo. Cẩn thận bắt assertion nếu cần.


def test_target_prompt_empty_input_loop():
    """Test Interactive Mode: Selecting an option and providing empty input loops prompt."""
    child = pexpect.spawn(f"{sys.executable} {MR_HOLMES_SCRIPT}", cwd=PROJECT_ROOT, encoding='utf-8')
    
    idx = child.expect([r'\(Y/N\)', r'-->', pexpect.EOF], timeout=10)
    if idx == 0:
        child.sendline('y')
        child.expect(r'-->', timeout=10)

    # Chọn 1 - Username OSINT
    child.sendline('1')

    # Yêu cầu nhập username (prompt "-->")
    child.expect(r'-->', timeout=10)
    
    # Nhập rỗng (Enter) => Gây loop hỏi lại
    child.sendline('')
    child.expect(r'-->', timeout=10) # Bắt buộc phải hỏi lại
    
    # Xử lý thoát lặp vòng
    child.sendline('dummyuser123')
    
    # Nhánh này thường dẫn đến Prompt về Proxy
    # Nhưng ta sẽ đóng child process ngay đây để an toàn (ko gửi req giả)
    child.close(force=True)


def test_proxy_yes_no_branch():
    """Test Interactive Mode: Navigating proxy options after entering target."""
    child = pexpect.spawn(f"{sys.executable} {MR_HOLMES_SCRIPT}", cwd=PROJECT_ROOT, encoding='utf-8')
    
    idx = child.expect([r'\(Y/N\)', r'-->', pexpect.EOF], timeout=10)
    if idx == 0:
        child.sendline('y')
        child.expect(r'-->', timeout=10)
        
    child.sendline('1')            # Option 1
    child.expect(r'-->', timeout=5)
    child.sendline('dummyuser_test_proxy') # Username

    # Kiểm tra Prompt hỏi Proxy
    # Note: Lần chạy test có thể có prompt proxy khác nhau (ví dụ: Y/N proxy)
    # Nếu MrHolmes in ra thông báo Proxy:
    idx2 = child.expect([r'YES\(2\)NO', pexpect.EOF], timeout=10)
    if idx2 == 0:
        # Nhập 2 = NO
        child.sendline('2')
    
    child.close(force=True)

@pytest.mark.parametrize("menu_option", [
    '2', '3', '7', '8', '9', '10', '11', '12', '13'
])
def test_interactive_osint_menus(menu_option):
    """Test Interactive Mode: Navigating OSINT menus that require a parameter prompt."""
    child = pexpect.spawn(f"{sys.executable} {MR_HOLMES_SCRIPT}", cwd=PROJECT_ROOT, encoding='utf-8')
    
    idx = child.expect([r'\(Y/N\)', r'-->', pexpect.EOF], timeout=10)
    if idx == 0:
        child.sendline('y')
        child.expect(r'-->', timeout=10)
        
    # Chọn Menu
    child.sendline(menu_option)

    # Đợi Prompt yêu cầu tham số
    child.expect(r'-->', timeout=10)
    
    # Gửi tham số giả và đóng process sớm
    child.sendline('dummy_parameter')
    
    # Thoát an toàn tránh request network
    child.close(force=True)

@pytest.mark.parametrize("menu_option", ['4', '14'])
def test_interactive_submenu_menus(menu_option):
    """Test Interactive Mode: Navigating to Submenus (Config / Session)."""
    child = pexpect.spawn(f"{sys.executable} {MR_HOLMES_SCRIPT}", cwd=PROJECT_ROOT, encoding='utf-8')
    
    idx = child.expect([r'\(Y/N\)', r'-->', pexpect.EOF], timeout=10)
    if idx == 0:
        child.sendline('y')
        child.expect(r'-->', timeout=10)
        
    child.sendline(menu_option)
    
    # Chờ prompt submenu hoặc ký tự bất kỳ rồi thoát
    idx2 = child.expect([r'-->', pexpect.EOF, pexpect.TIMEOUT], timeout=5)
    
    child.close(force=True)
    assert idx2 != 2 # Fail nếu timeout xảy ra

