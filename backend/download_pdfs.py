"""
下载并提取国家疾控局和国家卫健委的PDF文件
"""
import requests
from bs4 import BeautifulSoup
import os

# 需要下载的PDF文件
PDF_SOURCES = [
    {
        "id": "ndcpa_mpox_prevention_plan",
        "page_url": "https://www.ndcpa.gov.cn/jbkzzx/c100014/common/content/content_1698984403881291776.html",
        "title": "猴痘防控方案",
        "source": "国家疾控局",
        "region": "中国",
        "priority": 1,
        "topic": ["防控方案", "政策", "就医指导", "疫情监测"]
    },
    {
        "id": "nhc_mpox_technical_guide_2022",
        "page_url": "https://www.nhc.gov.cn/yjb/c100058/202207/fdaf10006d0b4034bca46a28b5f0bd20.shtml",
        "title": "猴痘防控技术指南（2022年版）",
        "source": "国家卫健委",
        "region": "中国",
        "priority": 1,
        "topic": ["技术指南", "防控", "诊断", "治疗", "隔离"]
    }
]


def find_pdf_link(page_url: str) -> str:
    """从网页中查找PDF下载链接"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(page_url, headers=headers, timeout=30)
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找PDF链接
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if '.pdf' in href.lower() or 'pdf' in link.get_text().lower():
                # 处理相对路径
                if href.startswith('http'):
                    return href
                elif href.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(page_url)
                    return f"{parsed.scheme}://{parsed.netloc}{href}"
                else:
                    base_url = page_url.rsplit('/', 1)[0]
                    return f"{base_url}/{href}"

        return None
    except Exception as e:
        print(f"  ❌ 查找PDF链接失败: {e}")
        return None


def download_pdf(pdf_url: str, output_path: str) -> bool:
    """下载PDF文件"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        print(f"  正在下载: {pdf_url}")
        response = requests.get(pdf_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = os.path.getsize(output_path)
        print(f"  ✓ 下载成功: {file_size} 字节")
        return True

    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return False


def process_pdfs():
    """处理PDF文件"""
    print("="*80)
    print("下载国家疾控局和国家卫健委的PDF文件")
    print("="*80)

    for i, source in enumerate(PDF_SOURCES, 1):
        print(f"\n[{i}/{len(PDF_SOURCES)}] {source['title']}")
        print(f"  来源: {source['source']}")

        # 查找PDF链接
        pdf_url = find_pdf_link(source['page_url'])

        if not pdf_url:
            print(f"  ⚠️  未找到PDF下载链接")
            continue

        # 下载PDF
        output_dir = f"data/pdf/{source['source']}"
        output_path = f"{output_dir}/{source['id']}.pdf"

        success = download_pdf(pdf_url, output_path)

        if success:
            print(f"  ✓ 已保存到: {output_path}")
        else:
            print(f"  ❌ 下载失败")

    print(f"\n{'='*80}")
    print("PDF下载完成")
    print(f"{'='*80}")
    print("\n注意：PDF文件需要使用专门的工具提取文本内容")
    print("建议：")
    print("1. 手动下载PDF文件")
    print("2. 使用PDF阅读器复制文本内容")
    print("3. 将内容保存为txt文件放入 data/raw/ 目录")
    print("4. 运行 python process_data_real.py 处理数据")


if __name__ == "__main__":
    print("国家疾控局和国家卫健委PDF文件下载工具\n")
    process_pdfs()
