# -*- coding: utf-8 -*-

import pandas as pd
import pandas 
from pytrends.request import TrendReq 
import time
import datetime as dt
from datetime import datetime, timedelta
import math
from time import gmtime, strftime
import telebot
import sys
import requests

if sys.version_info[0] < 3: 
    from StringIO import StringIO
else:
    from io import StringIO

def download_data(url, name):
#### connect to google
		_pytrends = TrendReq(hl='en-US', tz=360)
		#### build the playload
		_kw_list = [name]
		name_trend  = _kw_list[0]
		_cat = 0
		_geo = ''
		_gprop = ''
		# dates can be formated as  `2017-12-07 2018-01-07`, or  `today 3-m` `today 5-y`  check trends.google.com's url
		_date_fmt = '%Y-%m-%d'
		_start_date, _end_date = map(lambda x : dt.datetime.strptime(x, _date_fmt)
														   , [str(datetime.now()- timedelta(days=30))[:10]\
																  , str(datetime.now())[:10]])
		### Building an array of 90d periods to retreive google trend data with a one day resolution
		_90d_periods = math.ceil( (_end_date - _start_date) / dt.timedelta(days=90) )
		# _tmp_range is a list of dates separated by 90d.  We need one more than the number of _90_periods.  if _end_date is in the future google returns the most recent data
		_tmp_range = pd.date_range(start= _start_date, periods= _90d_periods + 1, freq= '90D')
		# making the list of `_start_date _end_date`, strf separated by a space
		_rolling_dates = [ ' '.join(map(lambda x : x.strftime(_date_fmt)
																		, [_tmp_range[i], _tmp_range[i+1] ])
																)
												for i in range(len(_tmp_range)-1) ]
		# initialization of the major data frame _df_trends
		# _dates will contains our last playload argument
		_dates = _rolling_dates[0]
		_pytrends.build_payload(_kw_list, cat=_cat, timeframe=_dates, geo=_geo, gprop=_gprop)
		_df_trends= _pytrends.interest_over_time()
		for _dates in _rolling_dates[1:] :
				# we need to normalize data before concatanation
				_common_date = _dates.split(' ')[0]
				_pytrends.build_payload(_kw_list, cat=_cat, timeframe=_dates, geo=_geo, gprop=_gprop)
				_tmp_df =   _pytrends.interest_over_time()
				_multiplication_factor = _df_trends.loc[_common_date] / _tmp_df.loc[_common_date]
				_df_trends= (pd.concat([_df_trends,
														   (_tmp_df[1:]* _multiplication_factor)])
										 .drop(labels = 'isPartial', axis = 1)  # isPartial usefull ?
										 .resample('D', closed='right').bfill()  # making sure that we have one value per day.
										)
		#coinmetrics bypass
		_headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
		_result = requests.get(url, headers = _headers)
		_r = _result.content.decode()
		TESTDATA = StringIO(_r)
		data_cm = pandas.read_csv(TESTDATA, sep=",")
		
		data_cm = data_cm.set_index('date')
		df_price = data_cm[data_cm.index > '2016-08-01'][['price(USD)', 'exchangeVolume(USD)']]
		df_price = df_price.join(_df_trends, how='outer')
		df_price = df_price.drop(['isPartial'], axis=1)
		df_price = df_price.dropna()
		df_price.columns = ['price','volume','combo']
		return df_price

data_url = pandas.read_csv('urls.csv')

r = ''

bot = telebot.TeleBot("key")
q = 0

for i_x in range(len(data_url)):
		min_bal = 1000
		time.sleep(5)
		url = data_url.url.iloc[i_x]
		name = data_url.name.iloc[i_x]
		df_price = download_data(url,name)
		if df_price.volume.mean() < 5*10**6:
			continue
		if q == 0:
			r = 'Colleagues, good afternoon. Current update on Google Trends('+str(df_price[::-1].head(7).index[0].strftime('%d-%m-%Y'))+')\n'
			bot.send_message('chat_id', r)
			q = 1
			
		df = df_price.dropna()
		deriv_trends = df[::-1].head(1).combo.mean() / df[::-1].head(7).combo.mean() -1
		deriv_price = df[::-1].head(1).price.mean() / df[::-1].head(7).price.mean() -1
		if deriv_trends > 0.1:
				r = name+': trend change (relative to 7-day MA)'+ str(int(deriv_trends*100))+'%, volume trading= $' + str(int(df[::-1].head(7).volume.mean()/ 10**6)) + ' mn (7-day MA), price change (relative to 7-day MA) = ' + str(int(deriv_price*100))+'%\n'
				bot.send_message('chat_id', r)
