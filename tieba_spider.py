import requests
import time
import json
import os
import shutil
import argparse

class TiebaSpider:
    def __init__(self):
        self.base_url = "https://tb.anova.me/getPostsNew"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        }
        self.all_posts = []
        self.raw_data_dir = "raw_data"  # raw数据保存目录
        self.processed_data_file = "processed_posts.json"  # 处理后数据保存文件
        
        # 创建raw数据目录
        if not os.path.exists(self.raw_data_dir):
            os.makedirs(self.raw_data_dir)
    
    def crawl_user_posts(self, username):
        """
        爬取指定用户的贴吧发言，直到没有更多数据为止
        :param username: 目标用户名
        :return: 所有爬取到的发言列表
        """
        print(f"开始爬取用户 [{username}] 的贴吧发言...")
        self.all_posts.clear()
        
        page = 1
        max_retries = 3  # 最大重试次数
        retry_delay = 5  # 重试间隔，秒
        
        while True:
            params = {
                "fname": "",  # 贴吧名，留空表示所有贴吧
                "username": username,
                "page": page
            }
            
            retries = 0
            success = False
            
            while retries < max_retries and not success:
                try:
                    print(f"正在获取第 {page} 页...")
                    response = requests.get(self.base_url, params=params, headers=self.headers, timeout=15)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"第 {page} 页获取成功，状态: {data.get('status')}")
                            
                            # 保存raw数据到文件
                            raw_filename = os.path.join(self.raw_data_dir, f"{username}_page_{page}.json")
                            with open(raw_filename, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            print(f"第 {page} 页原始数据已保存到 {raw_filename}")
                            
                            # 解析数据
                            self.parse_posts(data, page)
                            
                            # 检查当前页是否有数据
                            current_posts = []
                            if isinstance(data, dict) and 'posts' in data:
                                current_posts = data['posts']
                            
                            if len(current_posts) == 0:
                                # 当前页没有数据，尝试重试
                                no_data_retry = 0
                                max_no_data_retry = 5
                                no_data_delay = 3
                                
                                while no_data_retry < max_no_data_retry:
                                    no_data_retry += 1
                                    print(f"当前页没有数据，{no_data_delay}秒后进行第 {no_data_retry}/{max_no_data_retry} 次重试...")
                                    time.sleep(no_data_delay)
                                    
                                    # 重新请求当前页
                                    try:
                                        print(f"正在重试获取第 {page} 页...")
                                        retry_response = requests.get(self.base_url, params=params, headers=self.headers, timeout=15)
                                        if retry_response.status_code == 200:
                                            retry_data = retry_response.json()
                                            retry_posts = []
                                            if isinstance(retry_data, dict) and 'posts' in retry_data:
                                                retry_posts = retry_data['posts']
                                            
                                            if len(retry_posts) > 0:
                                                print(f"重试成功，第 {page} 页获取到 {len(retry_posts)} 条数据")
                                                # 保存重试后的raw数据
                                                retry_raw_filename = os.path.join(self.raw_data_dir, f"{username}_page_{page}_retry_{no_data_retry}.json")
                                                with open(retry_raw_filename, 'w', encoding='utf-8') as f:
                                                    json.dump(retry_data, f, ensure_ascii=False, indent=2)
                                                print(f"第 {page} 页重试原始数据已保存到 {retry_raw_filename}")
                                                
                                                # 解析重试后的数据
                                                self.parse_posts(retry_data, page)
                                                # 保存处理后的数据
                                                self.save_to_file(f"{username}_posts.json")
                                                break
                                    except Exception as e:
                                        print(f"重试失败: {e}")
                                
                                # 如果所有重试都没有数据，结束爬取
                                if no_data_retry >= max_no_data_retry:
                                    print("所有重试都没有数据，结束爬取")
                                    success = True
                                    # 保存最终数据
                                    self.save_to_file(f"{username}_posts.json")
                                    return self.all_posts
                            
                            # 检查是否还有更多数据
                            if not self.has_more_data(data):
                                print("已获取所有数据，结束爬取")
                                success = True
                                # 保存最终数据
                                self.save_to_file(f"{username}_posts.json")
                                return self.all_posts
                            
                            success = True
                            
                            # 即时保存处理后的数据
                            self.save_to_file(f"{username}_posts.json")
                            
                        except json.JSONDecodeError:
                            print(f"第 {page} 页返回数据不是JSON格式，尝试重试 {retries+1}/{max_retries}")
                            print(f"原始响应: {response.text[:300]}...")
                            retries += 1
                            if retries < max_retries:
                                print(f"{retry_delay}秒后重试...")
                                time.sleep(retry_delay)
                            else:
                                print("重试次数耗尽，跳过该页")
                                success = True  # 跳过该页，继续下一页
                                
                        except Exception as e:
                            print(f"第 {page} 页解析数据时发生错误: {e}，尝试重试 {retries+1}/{max_retries}")
                            retries += 1
                            if retries < max_retries:
                                print(f"{retry_delay}秒后重试...")
                                time.sleep(retry_delay)
                            else:
                                print("重试次数耗尽，跳过该页")
                                success = True  # 跳过该页，继续下一页
                                
                    else:
                        print(f"第 {page} 页请求失败，状态码: {response.status_code}，尝试重试 {retries+1}/{max_retries}")
                        print(f"响应内容: {response.text[:300]}...")
                        retries += 1
                        if retries < max_retries:
                            print(f"{retry_delay}秒后重试...")
                            time.sleep(retry_delay)
                        else:
                            print("重试次数耗尽，跳过该页")
                            success = True  # 跳过该页，继续下一页
                            
                except requests.RequestException as e:
                    print(f"第 {page} 页请求过程中发生错误: {e}，尝试重试 {retries+1}/{max_retries}")
                    retries += 1
                    if retries < max_retries:
                        print(f"{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        print("重试次数耗尽，跳过该页")
                        success = True  # 跳过该页，继续下一页
            
            if not success:
                break
            
            # 礼貌延时，避免被封IP
            time.sleep(2)  # 增加延时，减少被封概率
            page += 1
        
        # 保存最终数据
        self.save_to_file(f"{username}_posts.json")
        print(f"爬取完成！共获取到 {len(self.all_posts)} 条发言")
        return self.all_posts
    
    def parse_posts(self, data, page):
        """
        解析获取到的帖子数据
        :param data: 原始JSON数据
        :param page: 当前页码
        """
        # 根据接口返回的实际结构解析数据
        # 首先打印完整数据结构，方便调试
        if page == 1:
            print("\n=== 数据结构示例 ===")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:1500] + "...")
            print("===================\n")
        
        # 实际数据在 posts 字段中
        posts = []
        if isinstance(data, dict):
            if 'posts' in data:
                posts = data['posts']
        
        # 遍历处理每条帖子
        for i, post in enumerate(posts):
            post_info = {
                'id': i + 1 + (page - 1) * 20,  # 简单生成序号
                'title': post.get('title', ''),
                'content': post.get('content', ''),
                'href': post.get('href', ''),
                # 从href中提取贴吧名
                'forum': self.extract_forum_from_href(post.get('href', ''))
            }
            
            self.all_posts.append(post_info)
            
            # 打印部分信息
            print(f"  [{post_info['id']}] {post_info['forum']} - {post_info['title'][:20]}...")
    
    def extract_forum_from_href(self, href):
        """
        从帖子链接中提取贴吧名
        :param href: 帖子链接
        :return: 贴吧名
        """
        if not href:
            return ""
        # 示例链接：https://tieba.baidu.com/p/1234567890
        # 从帖子内容或其他方式提取贴吧名
        # 由于接口返回中没有直接提供贴吧名，我们可以从标题或内容中提取
        # 这里暂时返回一个占位符，实际使用时可以根据需要修改
        return "贴吧"
    
    def has_more_data(self, data):
        """
        检查是否还有更多数据
        :param data: 当前页数据
        :return: 是否还有更多数据
        """
        # 根据实际接口返回判断是否还有更多数据
        if isinstance(data, dict):
            # 检查posts列表长度，如果为0，说明没有更多数据
            if 'posts' in data:
                posts = data['posts']
                if len(posts) == 0:
                    return False
        
        return True
    
    def save_to_file(self, filename="tieba_posts.json"):
        """
        将爬取到的发言保存到JSON文件
        :param filename: 保存文件名
        """
        if not self.all_posts:
            print("没有数据可以保存")
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.all_posts, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到 {filename}")
        except Exception as e:
            print(f"保存文件时发生错误: {e}")

def main():
    """
    主函数，用于测试爬虫
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="百度贴吧用户发言爬虫")
    parser.add_argument("-u", "--username", type=str, help="要爬取的用户名")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 获取用户名
    username = args.username
    if not username:
        username = input("请输入要爬取的用户名: ").strip()
        if not username:
            print("错误：必须提供用户名")
            print("使用示例：python tieba_spider.py -u 用户名")
            return
    
    spider = TiebaSpider()
    # 爬取所有数据，直到没有更多数据为止
    posts = spider.crawl_user_posts(username)
    
    # 保存数据到文件
    spider.save_to_file(f"{username}_posts.json")
    
    # 打印统计信息
    if posts:
        print("\n=== 爬取统计 ===")
        print(f"总发言数: {len(posts)}")
        
        # 统计各贴吧发言数量
        forum_stats = {}
        for post in posts:
            forum = post['forum']
            forum_stats[forum] = forum_stats.get(forum, 0) + 1
        
        print("\n各贴吧发言分布:")
        for forum, count in sorted(forum_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {forum}: {count} 条")

if __name__ == "__main__":
    main()