# !usr/bin/env python3
# -*- coding:utf-8 _*-  
""" 
@author:dandan.zheng 
@file: calculater.py 
@time: 2018/03/15 
"""

# 输出税后工资
# 计算过程需要扣除社会保险费用
# 支持多人同时计算工资
# 打印税后工资列表

import sys, csv
from multiprocessing import Queue, Process


# 税率配置
class Config(object):

    def __init__(self,value):
        self.file_path = value
        # print (self.file_path)

    def get_config_item(self, key):
        try:
            with open(self.file_path, 'r', encoding='UTF-8') as file:
                for str_line in file:
                    list_line = str_line.split('=')
                    # print(list_line)
                    if list_line[0].strip() == key:
                        # print (float(list_line[1].strip()))
                        return  float(list_line[1].strip())
            return 0
        except FileNotFoundError:
            print ('FileNotFoundError')
            exit(-1)


# 用户信息
class UserWage(object):

    def __init__(self, value):
        self.file_path = value

    def get_user_wage(self):
        result = {}
        with open(self.file_path, 'r') as file:
            file_content = csv.reader(file)
            for line in file_content:
                result[line[0]] = float(line[-1])
        return result

    def write_list_to_file(self,data):
        with open(self.file_path,'a',newline = "") as file:
            writer = csv.writer(file,dialect = "excel")
            writer.writerows(data)


def calc_real_wages(job_num,wages,JShuL,JShuH,YangLao,YiLiao,ShiYe,GongShang,ShengYu,GongJiJin):
    # JiShuL 为社保缴费基数的下限，即工资低于 JiShuL 的值的时候，需要按照 JiShuL 的数值乘以缴费比例来缴纳社保。
    # JiShuH 为社保缴费基数的上限，即工资高于 JiShuH 的值的时候，需要按照 JiShuH 的数值乘以缴费比例缴纳社保。
    ji_shu = wages
    if wages < JShuL:
        ji_shu = JShuL

    if wages > JShuH:
        ji_shu = JShuH

    # 应交保险 养老保险：8 %; 医疗保险：2 %; 失业保险：0.5 %; 工伤保险：0 %; 生育保险：0 %; 公积金：6 %

    insurance = ji_shu * (YangLao + YiLiao + ShiYe + GongShang + ShengYu+ GongJiJin)

    # 起征点
    threshold = 3500

    # 应纳税所得额 = 工资金额 － 各项社会保险费 - 起征点(3500元)
    pay_taxes_amount = wages - insurance - threshold

    # 全月应纳税额	税率	速算扣除数（元）
    # 不超过 1500 元	3%	0
    # 超过 1500 元至 4500 元	10%	105
    # 超过 4500 元至 9000 元	20%	555
    # 超过 9000 元至 35000 元	25%	1005
    # 超过 35000 元至 55000 元	30%	2755
    # 超过 55000 元至 80000 元	35%	5505
    # 超过 80000 元	45%	13505
    taxes_rate = 0.03
    quick_calculation_deduction = 0

    if pay_taxes_amount <= 1500:
        taxes_rate = 0.03
        quick_calculation_deduction = 0
    elif pay_taxes_amount <= 4500:
        taxes_rate = 0.1
        quick_calculation_deduction = 105
    elif pay_taxes_amount <= 9000:
        taxes_rate = 0.2
        quick_calculation_deduction = 555
    elif pay_taxes_amount <= 35000:
        taxes_rate = 0.25
        quick_calculation_deduction = 1005
    elif pay_taxes_amount <= 55000:
        taxes_rate = 0.3
        quick_calculation_deduction = 2755
    elif pay_taxes_amount < 80000:
        taxes_rate = 0.35
        quick_calculation_deduction = 5505
    else:
        taxes_rate = 0.45
        quick_calculation_deduction = 13505

    # 应纳税额 = 应纳税所得额 × 税率 － 速算扣除数
    taxes_amount = pay_taxes_amount * taxes_rate - quick_calculation_deduction

    # 3500一下特殊处理
    if wages <= 3500:
        taxes_amount = 0

    # 实际工资
    real_wages = wages - insurance - taxes_amount

    # 特殊处理
    if real_wages < 0:
        real_wages = 0
    # 工号, 税前工资, 社保金额, 个税金额, 税后工资
    # print ([job_num, wages, format(insurance,'.2f'), format(taxes_amount,'.2f'), format(real_wages,'.2f')])
    return [job_num, int(wages), format(insurance,'.2f'), format(taxes_amount,'.2f'), format(real_wages,'.2f')]


def get_user_info(file_path, queue):
    user = UserWage(file_path)
    user_data = user.get_user_wage()
    queue.put(user_data)


def calculate_salary(file_path, queue_in, queue_out):
    all_salary_data=[]
    user_data = queue_in.get()
    config = Config(file_path)
    JShuL = config.get_config_item('JiShuL')
    JShuH = config.get_config_item('JiShuH')
    YangLao = config.get_config_item('YangLao')
    YiLiao = config.get_config_item('YiLiao')
    ShiYe = config.get_config_item('ShiYe')
    GongShang = config.get_config_item('GongShang')
    ShengYu = config.get_config_item('ShengYu')
    GongJiJin = config.get_config_item('GongJiJin')

    for user_num, wage in user_data.items():
        # 计算工资
        wage_detail = calc_real_wages(user_num, wage, JShuL, JShuH, YangLao, YiLiao, ShiYe, GongShang, ShengYu,GongJiJin)
        all_salary_data.append(wage_detail)
    queue_out.put(all_salary_data)


def save_salary(filepath, queue):
    salary_data = queue.get()
    save_wage = UserWage(filepath)
    save_wage.write_list_to_file(salary_data)


def main():
    # 取参数文件

    args = sys.argv[1:]
    param_c_index = args.index('-c')
    tax_config_path = args[param_c_index+1]

    param_d_index = args.index('-d')
    usr_info_config_path = args[param_d_index+1]

    param_o_index = args.index('-o')
    wages_detail_config_path = args[param_o_index + 1]

    user_2_salary_queue = Queue()
    salary_2_file_queue = Queue()

    Process(target=get_user_info,args=(usr_info_config_path,user_2_salary_queue)).start()
    Process(target=calculate_salary,args=(tax_config_path,user_2_salary_queue,salary_2_file_queue)).start()
    Process(target=save_salary,args=(wages_detail_config_path,salary_2_file_queue)).start()


if __name__ == '__main__':
    main()