# 导入必要的库
import backtrader as bt  # 量化交易回测框架
import pandas as pd  # 数据处理库
from backtrader_plotting import Bokeh  # 绘图插件
from backtrader_plotting.schemes import Tradimo # 插件自定义款式
import datetime as dt
# 定义SMA移动平均线策略类，继承自bt.Strategy
class SMAx2(bt.Strategy):
    params = (
        ('LowHi_price', 120),  # 最高最低价周期
    )

    def __init__(self):
        # 存储当前数据源的收盘价引用
        self.dataclose = self.data0.close  # 获取数据源的收盘价
        # 初始化订单、买入价格和佣金变量
        self.order = None  # 跟踪当前订单状态
        self.buyprice = None  # 记录买入价格
        self.buycomm = None  # 记录买入佣金
        self.sellprice = None  # 记录卖出价格

        #创建周期最高最低价
        self.highest = bt.indicators.Highest(period=self.p.LowHi_price, plotmaster=self.data0)
        self.lowest = bt.indicators.Lowest(period=self.p.LowHi_price, plotmaster=self.data0)
        self.sma_k = bt.talib.SMA(self.dataclose, timeperiod=11)  # talib 是独立的 bt内部有调用接口# 快均线
        self.sma_m = bt.talib.SMA(self.dataclose, timeperiod=350)  # talib 是独立的 bt内部有调用接口# 慢均线
        self.sma_j = bt.talib.SMA(self.dataclose, timeperiod=598)  # 趋势线
        # 初始化胜率和盈亏比统计变量
        self.winning_trades = 0  # 盈利交易次数
        self.losing_trades = 0  # 亏损交易次数
        self.total_won = 0.0  # 总盈利金额
        self.total_lost = 0.0  # 总亏损金额
        self.total_commission = 0.0  # 总手续费

    # 每个K线周期调用的核心交易逻辑
    def next(self):

        if not self.position:
            if self.data.high[0] > self.sma_j  and abs(self.sma_m[-5]-self.sma_m[0])>0.9:
                if (self.data.high[-6] < self.sma_m[-6] and self.data.high[0] > self.sma_m[0])or(
                        self.sma_k[-1] < self.sma_m[-1] and self.sma_k[0] > self.sma_m[0])or self.sma_m[-1] < self.sma_j[-1] and self.sma_m[0] > self.sma_j[0]:
                    self.buy()
            if self.data.low[0] < self.sma_j  and abs(self.sma_m[-5]-self.sma_m[0])>0.9:
                if (self.data.high[-6] > self.sma_m[-6] and self.data.high[0] < self.sma_m[0]) or (
                        self.sma_k[-1] > self.sma_m[-1] and self.sma_k[0] < self.sma_m[0])or self.sma_m[-1] > self.sma_j[-1] and self.sma_m[0] < self.sma_j[0] :
                    self.sell()
        if self.position.size > 0:
            zhisun = self.zhisun()-10
            if self.data.close[0] < zhisun or self.data.close[0] < self.sma_m[0]:
                self.close()


        if self.position.size < 0:
            zhisun = self.zhisun()+10
            if self.data.close[0] > zhisun or self.data.close[0] > self.sma_m[0]:
                self.close()

    def zhisun(self,):
        d = 0
        zhisun_1 = 0
        zhisun_2 = 0
        if self.position.size > 0:  # 多单
            for i in range(1, 200):
                if (self.data.open[-i - 1] > self.data.close[-i - 1] and
                        (self.data.open[-i] < self.data.close[-i] or self.data.open[-i] == self.data.close[-i])):
                    d += 1
                    zhisun_1 = (self.data.low[-i])  # 保存当前的最低价作为止损值
                    if d == 1:
                        zhisun_2 = zhisun_1  # 保存第一个止损值
                    if d == 2:
                        break
            return min(zhisun_1, zhisun_2)
        if self.position.size < 0:  # 空单
            for i in range(1, 200):
                if (self.data.open[-i - 1] < self.data.close[-i - 1] and
                        (self.data.open[-i] > self.data.close[-i] or self.data.open[-i] == self.data.close[-i])):
                    d += 1
                    zhisun_1 = (self.data.high[-i])  # 保存当前的最高价作为止损值
                    if d == 1:
                        zhisun_2 = zhisun_1  # 保存第一个止损值
                    if d == 2:
                        break
            return max(zhisun_1, zhisun_2)

    # 订单状态通知回调函数 以下为日志不参与策略算法
    def notify_order(self, order):
        """以下为日志不参与策略算法"""
        # 如果订单是提交/接受状态则直接返回
        if order.status in [order.Submitted, order.Accepted]:  # 订单已提交或已接受
            return

        # 如果订单已完成执行
        if order.status == order.Completed:  # 订单已完成
            # 如果是买入订单
            if order.isbuy():  # 判断是否为买入订单
                # 记录执行日志（价格、成本、佣金）
                self.log(f'BUY 买入执行 价格: {order.executed.price:.2f}, '
                         f'成本资金: {order.executed.value:.2f}, 佣金手续费:{order.executed.comm:.2f}')
                # 保存买入价格和佣金
                self.buyprice = order.executed.price  # 保存执行价格
                self.buycomm = order.executed.comm  # 保存执行佣金
            else:  # 卖出订单
                self.log(f'SELL 卖出执行 价格: {order.executed.price:.2f}, '
                         f'成本资金: {order.executed.value:.2f}, 佣金手续费:{order.executed.comm:.2f}')
                # 保存卖出价格
                self.sellprice = order.executed.price  # 保存执行价格
            # 记录订单执行的K线位置
            self.bar_executed = len(self)  # 记录执行时的K线位置

        # 订单取消/保证金不足/被拒绝的情况
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:  # 订单被取消、保证金不足或被拒绝
            self.log('保证金不足')  # 记录订单状态

        # 重置当前订单引用
        self.order = None  # 清空订单引用

    # 交易结果通知回调函数
    def notify_trade(self, trade):
        # 仅处理已平仓的交易
        if not trade.isclosed:  # 如果交易未平仓则返回
            return

        # 记录交易盈亏（毛收益和净收益）
        self.log(f'盈亏: 毛收益: {trade.pnl:.2f}, 净收益:{trade.pnlcomm:.2f}')

        # 统计胜率和盈亏比
        if trade.pnlcomm > 0:  # 如果净收益为正
            self.winning_trades += 1  # 增加盈利交易次数
            self.total_won += trade.pnlcomm  # 累计总盈利
        else:  # 如果净收益为负
            self.losing_trades += 1  # 增加亏损交易次数
            self.total_lost += abs(trade.pnlcomm)  # 累计总亏损（取绝对值）

        # 累计总手续费
        self.total_commission += trade.commission  # 累计总手续费

    # 自定义日志记录函数
    def log(self, txt, dt=None, doprint=True):
        # 如果允许打印
        if doprint:  # 判断是否允许打印
            # 获取当前K线时间（如果没有提供）
            dt = dt or self.datas[0].datetime.datetime(0)  # 获取当前K线时间
            # 打印带时间戳的日志（修改为显示到分钟）
            print(f'{dt.strftime("%Y-%m-%d %H:%M")}: {txt}')  # 格式化并打印日志


# 主程序入口
if __name__ == '__main__':
    # 1. 正确初始化Cerebro引擎（量化交易主引擎）
    cerebro = bt.Cerebro(stdstats=False)  # 注意：需要加括号()实例化   禁用默认观察者
    # 导入数据文件并处理
    shuju = 'SHFE.ru2509合约1分钟数据.csv'
    dataframe = pd.read_csv(  # 读取CSV数据文件
        shuju,  # 指定CSV文件路径
        parse_dates=['datetime'],  # 将datetime列解析为时间类型
        index_col='datetime'  # 直接将datetime列设为索引
    )
    #将1分钟数据压缩为5分钟数据
    dataframe = dataframe.resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    data_TALA = bt.feeds.PandasData(  # 创建Pandas数据源
        dataname=dataframe,  # 使用处理后的DataFrame
        datetime=None,  # 使用索引作为时间列
        open='open',  # 开盘价列名
        high='high',  # 最高价列名
        low='low',  # 最低价列名
        close='close',  # 收盘价列名
        volume='volume',  # 成交量列名
        name=shuju[0:-9],  # 设置报告标题#网页版报告必须设置否则报错
        # 设置数据时间范围
        # fromdate=dt.datetime(2025, 6, 30),  # 开始日期
        # todate=dt.datetime(2024, 7, 30),  # 结束日期
    )

    # 将数据添加到引擎
    cerebro.adddata(data_TALA)  # 将数据添加到Cerebro引擎

    # 添加策略到引擎
    cerebro.addstrategy(SMAx2)  # 添加SMA策略到引擎

    # 添加绩效分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='SharpeRatio')  # 夏普比率分析器
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DrawDown')  # 最大回撤分析器

    # 设置经纪人参数
    cs_ZJ = (100000.0)  # 设置初始资金
    cerebro.broker.setcash(cs_ZJ)
    # 降低交易佣金以减少手续费对结果的影响
    cerebro.broker.setcommission(commission=0.0004, mult=1)  # 交易佣金0.005%# 杠杆10倍

    # 调整仓位大小管理器，降低单次交易风险
    cerebro.addsizer(bt.sizers.PercentSizer, percents=98)  # 设置每次交易使用00%资金
    # 手动添加观察者
    cerebro.addobserver(bt.observers.BuySell)  # 观察交易信号
    cerebro.addobserver(bt.observers.Broker)  # 观察收益曲线
    cerebro.addobserver(bt.observers.Trades)  # 观察交易成功率
    # 执行回测
    results = cerebro.run()  # 运行回测
    # 获取第一个策略的运行结果
    strat = results[0]  # 获取策略实例
    # 打印回测结果

    print('夏普：', strat.analyzers.SharpeRatio.get_analysis()['sharperatio'])  # 打印夏普比率
    print('最大回撤：', f' {strat.analyzers.DrawDown.get_analysis()["max"]["drawdown"]}%')  # 打印最大回撤
    print('最大回撤金额：', f' {strat.analyzers.DrawDown.get_analysis()["max"]["moneydown"]}')
    print(f'初始资金:{cs_ZJ}')  # 打印初始资金
    print(f'最终资产:{(cerebro.broker.getvalue() - cs_ZJ) + cs_ZJ}')  # 打印最终资产
    print(f'总盈亏 :{(cerebro.broker.getvalue() - cs_ZJ)}')  # 打印总盈亏
    print(f'收益率 :{(((cerebro.broker.getvalue() - cs_ZJ)) / cs_ZJ * 100)}%')  # 打印收益率
    print(f'数据来源 :{shuju}')
    print('测试时间段：',
          f'{dataframe.index[0].strftime("%Y-%m-%d %H:%M")} 到 {dataframe.index[-1].strftime("%Y-%m-%d %H:%M")}')
    # 计算并打印胜率和盈亏比
    winning_trades = strat.winning_trades  # 获取盈利交易次数
    losing_trades = strat.losing_trades  # 获取亏损交易次数
    total_trades = winning_trades + losing_trades  # 计算总交易次数
    total_won = strat.total_won  # 获取总盈利
    total_lost = strat.total_lost  # 获取总亏损
    total_commission = strat.total_commission  # 获取总手续费

    if total_trades > 0:  # 如果总交易次数大于0
        win_rate = winning_trades / total_trades * 100  # 计算胜率
        print(f'胜率: {win_rate:.2f}% ({winning_trades}/{total_trades})')  # 打印胜率
    if losing_trades > 0:  # 如果亏损交易次数大于0
        avg_win = total_won / winning_trades if winning_trades > 0 else 0  # 计算平均盈利
        avg_loss = total_lost / losing_trades  # 计算平均亏损
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0  # 计算盈亏比
        print(f'盈亏比: {profit_loss_ratio:.2f} (平均盈利:{avg_win:.2f}/平均亏损:{avg_loss:.2f})')  # 打印盈亏比

    # 打印总手续费
    print(f'总手续费: {total_commission:.2f}')  # 打印总手续费

    # 绘制回测结果为图表 # 所有图表显示在单个窗口中# 图像尺寸 (宽度, 高度)  # 阳线颜色 (红色)     # 阴线颜色 (绿色)  # K线透明度
    # 默认的绘图
    # cerebro.plot(style='candlestick', numfigs=1, figsize=(16, 9),
    #              barup='#E74C3C', bardown='#2ECC71', baralpha=0.7, timeformat='%Y-%m-%d %H:%M')
    # 使用 backtrader_plotting 进行绘图
    # Bokeh绘图选项说明:
    # style参数可选值:
    # - 'bar': 柱状图样式
    # - 'line': 线图样式
    # scheme参数可选值:
    # - Tradimo: 传统金融图表配色方案
    # - Blackly: 暗色主题方案
    # - Customization:自定义方案
    # 例如: b = Bokeh(style='candle', scheme=Blackly())
    # output_mode是输出模式选择save为生成网站文件不打开，show生成文件并打开默认show
    # filename是自定义保存路径，不填默认生成为用户文件下的临时文件
    baogaomulu = (f'回测报告{shuju[0:-9]}回测报告.html')
    b = Bokeh(style='bar', scheme=Tradimo(), output_mode='show', filename=baogaomulu, voloverlay=False)
    cerebro.plot(b)  # 绘图用插件绘图
    print(f'报告已保存在:{baogaomulu}')
