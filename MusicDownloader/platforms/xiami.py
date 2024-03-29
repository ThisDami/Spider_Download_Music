'''
Function:
	虾米音乐下载: https://www.xiami.com/
'''
import os
import json
import click
import requests
from contextlib import closing
try:
	from urllib.parse import unquote
except ImportError:
	from urllib import unquote


'''
Function:
	破解虾米URL加密
'''
class ParseURL():
	def __init__(self):
		self.info = 'parse xiami url'
	def parse(self, location):
		rows, encryptUrl = int(location[:1]), location[1:]
		encryptUrlLen = len(encryptUrl)
		cols_base = encryptUrlLen // rows
		rows_ex = encryptUrlLen % rows
		matrix = []
		for row in range(rows):
			length = cols_base + 1 if row < rows_ex else cols_base
			matrix.append(encryptUrl[:length])
			encryptUrl = encryptUrl[length:]
		decryptUrl = ''
		for i in range(encryptUrlLen):
			decryptUrl += matrix[i % rows][i // rows]
		decryptUrl = unquote(decryptUrl).replace('^', '0')
		return 'https:' + decryptUrl


'''
Input:
	-mode: search(搜索模式)/download(下载模式)
		--search模式:
			----songname: 搜索的歌名
		--download模式:
			----need_down_list: 需要下载的歌曲名列表
			----savepath: 下载歌曲保存路径
Return:
	-search模式:
		--search_results: 搜索结果
	-download模式:
		--downed_list: 成功下载的歌曲名列表
'''
class xiami():
	def __init__(self):
		self.headers = {
						'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
						'referer': 'http://m.xiami.com/'
						}
		self.search_url = 'http://api.xiami.com/web'
		self.playlist_url = 'http://www.xiami.com/song/playlist/id/{}/object_name/default/object_id/0/cat/json'
		self.parser = ParseURL()
		self.session = requests.Session()
		self.session.headers.update(self.headers)
		self.session.head('http://m.xiami.com')
		self.search_results = {}
	'''外部调用'''
	def get(self, mode='search', **kwargs):
		if mode == 'search':
			songname = kwargs.get('songname')
			self.search_results = self.__searchBySongname(songname)
			return self.search_results
		elif mode == 'download':
			need_down_list = kwargs.get('need_down_list')
			downed_list = []
			savepath = kwargs.get('savepath') if kwargs.get('savepath') is not None else './results'
			if need_down_list is not None:
				for download_name in need_down_list:
					songid = self.search_results.get(download_name)
					try:
						res = requests.get(self.playlist_url.format(songid), headers=self.headers)
						songinfos = json.loads(res.text)
					except:
						continue
					location = songinfos['data']['trackList'][0]['location']
					if not location:
						continue
					download_url = self.parser.parse(location)
					res = self.__download(download_name, download_url, savepath)
					if res:
						downed_list.append(download_name)
			return downed_list
		else:
			raise ValueError('mode in xiami().get must be <search> or <download>...')
	'''下载'''
	def __download(self, download_name, download_url, savepath):
		if not os.path.exists(savepath):
			os.mkdir(savepath)
		download_name = download_name.replace('<', '').replace('>', '').replace('\\', '').replace('/', '') \
									 .replace('?', '').replace(':', '').replace('"', '').replace('：', '') \
									 .replace('|', '').replace('？', '').replace('*', '')
		savename = 'xiami_{}'.format(download_name)
		count = 0
		while os.path.isfile(os.path.join(savepath, savename+'.mp3')):
			count += 1
			savename = 'xiami_{}_{}'.format(download_name, count)
		savename += '.mp3'
		try:
			print('[xiami-INFO]: 正在下载 --> %s' % savename.split('.')[0])
			with closing(requests.get(download_url, headers=self.headers, stream=True, verify=False)) as res:
				total_size = int(res.headers['content-length'])
				if res.status_code == 200:
					label = '[FileSize]:%0.2f MB' % (total_size/(1024*1024))
					with click.progressbar(length=total_size, label=label) as progressbar:
						with open(os.path.join(savepath, savename), "wb") as f:
							for chunk in res.iter_content(chunk_size=1024):
								if chunk:
									f.write(chunk)
									progressbar.update(1024)
				else:
					raise RuntimeError('Connect error...')
			return True
		except:
			return False
	'''根据歌名搜索'''
	def __searchBySongname(self, songname):
		params = {
					"key": songname,
					"v": "2.0",
					"app_key": "1",
					"r": "search/songs",
					"page": 1,
					"limit": 20,
				}
		res = self.session.get(self.search_url, params=params)
		results = {}
		for song in res.json()['data']['songs']:
			if not song.get('listen_file'):
				continue
			songid = song.get('song_id')
			singers = song.get('artist_name')
			album = song.get('album_name')
			download_name = '%s--%s--%s' % (song.get('song_name'), singers, album)
			count = 0
			while download_name in results:
				count += 1
				download_name = '%s(%d)--%s--%s' % (song.get('song_name'), count, singers, album)
			results[download_name] = songid
		return results


'''测试用'''
if __name__ == '__main__':
	xiami_downloader = xiami()
	res = xiami_downloader.get(mode='search', songname='尾戒')
	xiami_downloader.get(mode='download', need_down_list=list(res.keys())[:9])