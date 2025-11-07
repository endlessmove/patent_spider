##########################
#         README         #
##########################
# 此demo没有断点续爬取功能，如果程序未能正常运行下去，大概率是被封禁IP
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
import numpy as np
import json
import os


DOWNLOAD_DIR  = os.path.abspath('./CNKI_Fire')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        
async def main(init_page, key_word, main_title, url, time_span):
    
    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=False)  
        context = await browser.new_context()
        page = await context.new_page()
        
        
        await page.goto(url)
        await page.fill("input[type='text']", key_word) 
        await asyncio.sleep(1)
        await page.click(".search-btn[type='button']")  # 点击搜索
        await asyncio.sleep(1)
        num_page = init_page
        
        # 按钮是js触发的,选择期刊论文，如何需要选择会议等其他模块，修改下方classid 
        # 》》》》》》》》》                                                     ⬇️
        await page.evaluate("""
        const el = document.querySelector("a[name='classify'][classid='YSTT4HG0']");
        if (el) {
        const ev1 = new MouseEvent('mouseover', { bubbles: true });
        const ev2 = new MouseEvent('mouseenter', { bubbles: true });
        el.dispatchEvent(ev1);
        el.dispatchEvent(ev2);
        }
        const li = document.querySelector("li.haschild.cur");
        if (li) {
        const submenu = li.querySelector("ul");
        if (submenu) submenu.style.display = 'block';
        }
        """)
        await page.wait_for_timeout(500)
        await page.click("a[name='classify'][classid='YSTT4HG0']")
        
        # 点击主题栏
        await asyncio.sleep(2.4)
        # await page.locator('dt.subtit.row-a2 a').nth(1).click()
        # 点击搜索关键词
        common_exit = False
        await page.evaluate("""
    document.querySelectorAll('.resultlist li').forEach(li => li.style.display = 'list-item');
""")
        checkbox_selector = f'dd[field="ZYZT"] input[type="checkbox"][value="{main_title}"]'
        await page.wait_for_selector(checkbox_selector)
        await asyncio.sleep(1.0)
        # 点击“电子设备”复选框
        await page.click(checkbox_selector)
        print(f"已点击[{main_title}]复选框")
        # 修改每页显示的专利数量
        # current_val = await page.locator("#perPageDiv .sort-default span").text_content()
        # if current_val.strip() != "50":
        #     await page.click("#perPageDiv .sort-default")
        #     await page.wait_for_selector("#perPageDiv .sort-list", state="visible")
        #     await page.click("#perPageDiv .sort-list li[data-val='50'] a")
        #     print("设置为每页 50 条")
        # else:
        #     print("已经是 50 条/页，无需修改")
        await asyncio.sleep(0.2)    
        # 点击“年度”标题展开下拉内容，这里有坑，点击后可能页面没反应
        await page.wait_for_function("window.filterFn !== undefined", timeout=10000)

        try:
            await page.evaluate("""
            () => {
                const dt = document.querySelector('dt.tit[groupid="YE"]');
                if (dt) {
                    dt.scrollIntoView({behavior: 'smooth', block: 'center'});
                    const ev1 = new MouseEvent('mousedown', {bubbles: true});
                    const ev2 = new MouseEvent('click', {bubbles: true});
                    dt.dispatchEvent(ev1);
                    dt.dispatchEvent(ev2);
                }
            }
            """)
            
            await page.wait_for_function("""
            () => {
                const ul = document.querySelector('dd[field="YE"] ul');
                return ul && ul.offsetParent !== null && ul.querySelectorAll('li').length > 0;
            }
            """, timeout=5000)
            print("年度筛选框已正常展开")

        except PWTimeout:
            print("下拉框未出现，尝试强制展开 DOM")
            await page.evaluate("""
            () => {
                const dl = document.querySelector('dl[groupid="YE"]');
                if (dl) {
                    dl.classList.remove('off');
                    dl.classList.add('on');
                }
                const dd = document.querySelector('dd[field="YE"]');
                if (dd) {
                    dd.style.display = 'block';
                    const ul = dd.querySelector('ul');
                    if (ul) {
                        ul.style.display = 'block';
                        ul.style.visibility = 'visible';
                        ul.style.height = 'auto';
                    }
                }
            }
            """)
            await page.wait_for_timeout(800)

        await page.wait_for_selector('dd[field="YE"] ul li', state='visible')
        if int(time_span) < 2016:
            print(f'准备搜索{time_span}年度论文信息')
            # await page.locator('a.btn').click()
            await page.evaluate("""
    document.querySelectorAll('.resultlist li').forEach(li => li.style.display = 'list-item');
""")

        checkbox_selector = f'dd[field="YE"] input[type="checkbox"][value="{time_span}"]'
        if await page.query_selector(checkbox_selector):
            await page.click(checkbox_selector)
            print(f"已点击年份：{time_span}")
        else:
            print(f"未找到年份 {time_span}")
        
        if num_page > 1:
            for i in range(1,num_page):
                next_button = "#PageNext"
                if await page.locator(next_button).is_visible():
                    old_page_num = await page.get_attribute(next_button, "data-curpage")
                
                    print(f"翻转至第{old_page_num}页 >>")
                    await page.click(next_button)
                    num = np.random.choice([0.2, 0.4, 0.6],1)
                    await asyncio.sleep(num)
                    await page.wait_for_function(
                            """
                            ([selector, oldVal]) => {
                                const el = document.querySelector(selector);
                                const curPage = el ? el.getAttribute('data-curpage') : null;
                                return curPage !== oldVal;
                            }
                            """,
                            arg=[next_button, old_page_num],
                            timeout=10000
                        )
                    num = np.random.choice([0.4,0.8,0.6],1)
                    await asyncio.sleep(num)
        
        while True:
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(0.3)
            await page.wait_for_selector("table.result-table-list")
            patent_links = await page.query_selector_all("a.fz14")      
            source_links = await page.query_selector_all("td.source")   
            print(f"开始获取当前第{num_page}页信息！！！")
            # 每一页保存一个文件，方便问题排查
            data_save= []
            for pl, sl in zip (patent_links,source_links):
                # 在新标签页打开
                try:
                    title = await pl.inner_text()
                    source = await sl.inner_text()
                    # print(f'标题：{title}, 期刊源：{source}')
                    data_save.append({'title':title,'source':source})
                except Exception as e:
                    print(f"提取信息失败：{e}")
                    
                num = np.random.choice([0.1,0.15,0.18],1)
                await asyncio.sleep(num)
                
            with open(os.path.join(DOWNLOAD_DIR,f'paper{main_title}_{time_span}_{num_page}.jsonl'),'w',encoding='utf-8') as f:
                for d in data_save:
                    f.write(json.dumps(d, ensure_ascii=False) + "\n")
            
            next_button = "#PageNext"
            if await page.locator(next_button).is_visible():
                old_page_num = await page.get_attribute(next_button, "data-curpage")
                now_page = int(old_page_num) -1
                print(f" ✔ 已经完成第{now_page}页的搜索。")
                await page.click(next_button)
                num = np.random.choice([0.2, 0.45, 0.4, 0.3],1)
                await asyncio.sleep(num)
                # await page.wait_for_function(
                #     "(selector, oldVal) => document.querySelector(selector)?.getAttribute('data-curpage') !== oldVal",
                #     next_button, old_page_num
                # )
                await page.wait_for_function(
                        """
                        ([selector, oldVal]) => {
                            const el = document.querySelector(selector);
                            const curPage = el ? el.getAttribute('data-curpage') : null;
                            return curPage !== oldVal;
                        }
                        """,
                        arg=[next_button, old_page_num],
                        timeout=10000
                    )
                await asyncio.sleep(0.2)
            else:
                
                print("到达最后一页。所有数据已获取！")
                common_exit = True
                break
           
            num_page += 1

        await browser.close()
        return num_page, common_exit


async def loop(init_page, key_word, main_title, url):

        tims = list(range(2025,2010,-1))  
        for val in tims:
            time_span = str(val)
            num, flag = await main(init_page, key_word, main_title, url, time_span)
            while not flag:
                num, flag = await main(num, key_word, url, time_span)
                await asyncio.sleep(10.0)  # 缓冲一下


if __name__ == "__main__":
    init_page = 1    # 起始页或者任意页面
    key_word = "xxxx"  # 搜索关键词
    main_title = "xxx"  # 主要主题
    url = "https://www.cnki.net/"  # 搜知网
    asyncio.run(loop(init_page, key_word, main_title, url))
