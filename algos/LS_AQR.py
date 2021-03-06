from QuantConnect.Data.UniverseSelection import *

class LongShortMultifactor(QCAlgorithm):

    def __init__(self):
    # Set rebalance flag
        self.reb = 1
    # Number of stocks to pass CoarseSelection process
        self.num_coarse = 300
    # Number of stocks to long/short
        self.winsorize = 10
        self.num_fine = 50
        self.symbols = None
    # Return
        self.daily_return = 0
        self.prev_value = self.Portfolio.TotalPortfolioValue

    def Initialize(self):
        self.SetWarmup(timedelta(20))
        self.SetCash(100000)
        self.SetStartDate(2014, 12, 1)
        self.SetEndDate(2017, 10, 1)

        self.spy = self.AddEquity("SPY", Resolution.Daily).Symbol

        self.UniverseSettings.Resolution = Resolution.Daily

        self.AddUniverse(self.CoarseSelectionFunction,self.FineSelectionFunction)

    # Schedule the rebalance function to execute at the begining of each month
        self.Schedule.On(self.DateRules.MonthStart(self.spy),
        self.TimeRules.AfterMarketOpen(self.spy,5), Action(self.rebalance))

        self.Schedule.On(self.DateRules.EveryDay(), \
                 self.TimeRules.BeforeMarketClose("SPY"), \
                 self.MarketClose)

    def CoarseSelectionFunction(self, coarse):
    # if the rebalance flag is not 1, return null list to save time.
        if self.reb != 1:
            return self.long + self.short

    # make universe selection once a month
    # drop stocks which have no fundamental data or have too low prices
        selected = [x for x in coarse if (x.HasFundamentalData)
                    and (float(x.Price) > 5)]

        sortedByDollarVolume = sorted(selected, key=lambda x: x.DollarVolume, reverse=True)
        top = sortedByDollarVolume[:self.num_coarse]
        return [i.Symbol for i in top]

    def FineSelectionFunction(self, fine):
    # return null list if it's not time to rebalance
        if self.reb != 1:
            return self.long + self.short

        self.reb = 0

    # drop stocks which don't have the information we need.
    # you can try replacing those factor with your own factors here

        filtered_fine = [x for x in fine if x.OperationRatios.OperationMargin.Value
                                        and x.ValuationRatios.PriceChange1M
                                        and x.ValuationRatios.BookValueYield]

        # rank stocks by three factor.
        sortedByfactor1 = sorted(filtered_fine, key=lambda x: x.OperationRatios.OperationMargin.Value, reverse=True)
        sortedByfactor2 = sorted(filtered_fine, key=lambda x: x.ValuationRatios.PriceChange1M, reverse=True)
        sortedByfactor3 = sorted(filtered_fine, key=lambda x: x.ValuationRatios.BookValueYield, reverse=True)

        stock_dict = {}

        # assign a score to each stock (ranking process)
        for i,ele in enumerate(sortedByfactor1):
            rank1 = i
            rank2 = sortedByfactor2.index(ele)
            rank3 = sortedByfactor3.index(ele)
            score = sum([rank1*0.3,rank2*0.3,rank3*0.4])
            stock_dict[ele] = score

        # sort the stocks by their scores
        self.sorted_stock = sorted(stock_dict.items(), key=lambda d:d[1],reverse=False)
        sorted_symbol = [x[0] for x in self.sorted_stock]

        # sort the top stocks into the long_list and the bottom ones into the short_list
        self.long = [x.Symbol for x in sorted_symbol[:self.num_fine]]
        self.short = [x.Symbol for x in sorted_symbol[-self.num_fine:]]

        return self.long + self.short

    def OnData(self, data):
        pass

    def MarketClose(self):
        self.daily_return = 100*((self.Portfolio.TotalPortfolioValue - self.prev_value)/self.prev_value)
        self.prev_value = self.Portfolio.TotalPortfolioValue
        self.Log(self.daily_return)
        return

    def rebalance(self):
    # Liquidate all stocks at end of month
        self.Liquidate()

        for i in self.long:
            self.SetHoldings(i, 0.9/self.num_fine)

        for i in self.short:
            self.SetHoldings(i, -0.9/self.num_fine)

        self.reb = 1
