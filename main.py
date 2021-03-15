import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns

pd.set_option('display.max_rows', None)
purchases = pd.read_csv("purchases.csv", delimiter='\t', decimal=',')
visits = pd.read_csv("visits.csv", delimiter='\t')
visits['end_ts'] = pd.to_datetime(visits['end_ts'], format='%Y-%m-%dT%H:%M:%S')
visits['start_ts'] = pd.to_datetime(visits['start_ts'], format='%Y-%m-%dT%H:%M:%S')
purchases['buy_ts'] = pd.to_datetime(purchases['buy_ts'], format='%d.%m.%Y %H:%M:%S')
revenue_sum = sum(purchases.revenue)
unique_count = purchases['uid'].nunique()
revenue_sum / unique_count
purchases['first_order_ts'] = purchases.groupby('uid')['buy_ts'].transform('min')
purchases['order_month'] = purchases['buy_ts'].astype('datetime64[M]')
purchases['first_order_month'] = purchases['first_order_ts'].astype('datetime64[M]')
user_source = (
    visits.sort_values(by='start_ts').groupby('uid', as_index=False).agg({'source_id': 'first'})
)

purchases = purchases.merge(user_source, on='uid')
visits['first_visit_ts'] = visits.groupby('uid')['start_ts'].transform('min')
first_visit_order = (
    purchases[['uid', 'first_order_ts']].merge(visits[['uid', 'first_visit_ts']], on='uid').drop_duplicates()
        .reset_index(drop=True)

)

# first_visit_order['days_before_order'] = (
#     (first_visit_order['first_order_ts'] - first_visit_order['first_visit_ts']).dt.days
# )

purchases['cohort_lifetime'] = (
        (purchases['order_month'] - purchases['first_order_month']) / np.timedelta64(1, 'M')
).round().astype('int')

cohort_buyers = (
    purchases.groupby(['first_order_month', 'cohort_lifetime'], as_index=False)
    .agg({'uid': ['nunique', 'count'], 'revenue': 'sum'})
)

cohort_buyers.columns = (
    ['first_order_month', 'cohort_lifetime', 'n_buyers', 'n_orders', 'revenue']
)
initial_buyers_count = (
    cohort_buyers
    .query('cohort_lifetime == 0')[['first_order_month', 'n_buyers']]
).rename(columns={'n_buyers': 'cohort_buyers'})

initial_orders_count = (
    cohort_buyers
    .query('cohort_lifetime == 0')[['first_order_month', 'n_orders']]
).rename(columns={'n_orders': 'cohort_orders'})

cohort_buyers = (
    cohort_buyers
    .merge(initial_buyers_count, on='first_order_month')
    .merge(initial_orders_count, on='first_order_month')
)

cohort_buyers['orders_per_buyer'] = cohort_buyers['n_orders'] / cohort_buyers['cohort_buyers']
purchases_per_buyer_pivot = (
    cohort_buyers
    .pivot_table(index='first_order_month',
                 columns='cohort_lifetime',
                 values='orders_per_buyer')
).cumsum(axis=1)

print(purchases_per_buyer_pivot)
fig, ax = plt.subplots(figsize=(13, 9))
sns.heatmap(purchases_per_buyer_pivot, annot=True, fmt='.2f', linewidths=2,
            linecolor='black', ax=ax)
ax.set_title('Среднее количество покупок на каждого покупателя')
ax.set_xlabel('Lifetime когорты')
ax.set_ylabel('Когорта')
plt.show()

cohort_buyers['revenue_per_buyer'] = cohort_buyers['revenue'] / cohort_buyers['n_orders']
revenue_per_buyer_pivot = (
    cohort_buyers
    .pivot_table(index='first_order_month',
                 columns='cohort_lifetime',
                 values='revenue_per_buyer')
)
print(revenue_per_buyer_pivot)
fig, ax = plt.subplots(figsize=(13, 9))
sns.heatmap(revenue_per_buyer_pivot, annot=True, fmt='.1f', linewidths=2,
            linecolor='black', ax=ax)
ax.set_title('Средний чек')
ax.set_xlabel('Lifetime когорты')
ax.set_ylabel('Когорта')
plt.show()

cohort_sizes = (
    cohort_buyers[['first_order_month', 'cohort_buyers']]
    .drop_duplicates()
    .reset_index(drop=True)
)
cohort_ltv = (
    purchases
    .groupby(['first_order_month', 'order_month'], as_index=False)
    .agg({'revenue': 'sum'})
)
report_ltv = cohort_sizes.merge(cohort_ltv, on='first_order_month')
margin_rate = 1

report_ltv['gp'] = report_ltv['revenue'] * margin_rate
report_ltv['cohort_lifetime'] = (
        (report_ltv['order_month'] - report_ltv['first_order_month']) / np.timedelta64(1, 'M')
).round().astype('int')
report_ltv['ltv'] = report_ltv['gp'] / report_ltv['cohort_buyers']

output_ltv = (
    report_ltv
        .pivot_table(index='first_order_month',
                     columns='cohort_lifetime',
                     values='ltv')
).cumsum(axis=1)

fig, ax = plt.subplots(figsize=(13, 9))
sns.heatmap(output_ltv, annot=True, fmt='.2f', linewidths=2,
            linecolor='black', ax=ax)
ax.set_title('LTV')
ax.set_xlabel('Lifetime когорты')
ax.set_ylabel('Когорта')
plt.show()


