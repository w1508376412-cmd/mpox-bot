"""
WHO Shiny Dashboard 爬虫 - 使用 Playwright 抓取动态数据
"""
from playwright.sync_api import sync_playwright
import time

def scrape_who_dashboard():
    """
    抓取 WHO Mpox 全球仪表盘的实时数据
    """
    url = "https://worldhealthorg.shinyapps.io/mpx_global/"
    
    with sync_playwright() as p:
        # 启动浏览器 (无头模式)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"正在访问 WHO 仪表盘: {url}")
        try:
            page.goto(url, wait_until="load", timeout=90000)
        except Exception as e:
            print(f"页面基础加载超时，尝试继续提取内容: {e}")
        
        # 等待 Shiny 内容加载 (通常有 "shiny-busy" class 消失)
        # 或者等待特定的数值卡片出现
        print("等待动态组件加载...")
        try:
            # 等待包含数值的元素出现
            page.wait_for_selector(".value-box, .info-box, .shiny-bound-output", timeout=60000)
            # 给一点额外的渲染时间
            time.sleep(10)
        except Exception as e:
            print(f"动态组件加载超时: {e}")
        
        # 提取页面所有文本内容
        content = page.content()
        
        # 获取所有统计卡片的信息
        # 针对 WHO Shiny App 的常见结构提取
        stats = page.evaluate("""
            () => {
                const results = [];
                // 尝试找到所有的 valueBox 或 infoBox
                const boxes = document.querySelectorAll('.small-box, .info-box, .value-box');
                boxes.forEach(box => {
                    results.push(box.innerText.replace(/\\n/g, ' ').trim());
                });
                return results;
            }
        """)
        
        if not stats:
            # 如果没找到特定的 box，提取主体文本
            print("未找到统计卡片，提取页面核心文本...")
            main_text = page.inner_text("body")
            # 简单清理
            summary = main_text[:2000] # 只取前2000字作为概要
        else:
            summary = "\\n".join(stats)

        browser.close()
        
        # 构造最终的结构化摘要
        final_summary = f"""
WHO Mpox Global Dashboard Summary (Automated Scrape at {time.strftime('%Y-%m-%d %H:%M:%S')})

Key Statistics Found on Dashboard:
{summary}

Source: {url}
Status: Successfully retrieved dynamic content.
"""
        return final_summary

if __name__ == "__main__":
    try:
        data = scrape_who_dashboard()
        print("\\n抓取成功：")
        print("-" * 40)
        print(data)
        print("-" * 40)
    except Exception as e:
        print(f"抓取失败: {e}")
