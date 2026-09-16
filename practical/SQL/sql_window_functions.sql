-- ==============================================================================
-- PROBLEM 1: Window Functions 
-- ==============================================================================

-- Show each order with a running total of total_amount for that customer,
-- ordered by order_date.
-- Practice SUM(...) OVER (...).

select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.order_date,
	o.total_amount,
	SUM(o.total_amount) over (partition by c.customer_id order by o.order_date) as running_total
	
	-- voy a sumar total amount particionado (dividido) por cada customer id y ordenado por order date
	-- a fin de cuentas lo que quiero hacer es mostrar como avanzo el gasto de cada cliente

from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- ==============================================================================
-- PROBLEM 2: Ranking orders per customer
-- ==============================================================================

-- ROW_NUMBER gives each order a unique position inside each customer's history.
-- Useful when you need "latest order per customer" or "first order per customer".
select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.order_date,
	o.total_amount,
	ROW_NUMBER() over (
		partition by c.customer_id
		order by o.order_date desc, o.order_id desc
	) as latest_order_rank
from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- Same idea, but filtering to only the most recent order per customer.
-- Many databases do not allow filtering directly on a window alias in WHERE,
-- so we calculate the ranking in a CTE first.
with ranked_orders as (
	select
		c.customer_id,
		c.customer_name,
		o.order_id,
		o.order_date,
		o.total_amount,
		ROW_NUMBER() over (
			partition by c.customer_id
			order by o.order_date desc, o.order_id desc
		) as latest_order_rank
	from
		customers c
	join orders o on
		c.customer_id = o.customer_id
)
select
	customer_id,
	customer_name,
	order_id,
	order_date,
	total_amount
from
	ranked_orders
where
	latest_order_rank = 1;

-- ==============================================================================
-- PROBLEM 3: RANK vs DENSE_RANK
-- ==============================================================================

-- RANK leaves gaps after ties. DENSE_RANK does not.
-- Example: amounts 100, 90, 90, 80
-- RANK:       1,  2,  2,  4
-- DENSE_RANK: 1,  2,  2,  3
select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.total_amount,
	RANK() over (
		partition by c.customer_id
		order by o.total_amount desc
	) as amount_rank,
	DENSE_RANK() over (
		partition by c.customer_id
		order by o.total_amount desc
	) as dense_amount_rank
from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- ==============================================================================
-- PROBLEM 4: Compare each order to the previous order
-- ==============================================================================

-- LAG looks backward inside the customer's ordered history.
-- This is useful for churn analysis, repeat purchase behavior, and trend checks.
select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.order_date,
	o.total_amount,
	LAG(o.order_date) over (
		partition by c.customer_id
		order by o.order_date, o.order_id
	) as previous_order_date,
	LAG(o.total_amount) over (
		partition by c.customer_id
		order by o.order_date, o.order_id
	) as previous_order_amount,
	o.total_amount - LAG(o.total_amount) over (
		partition by c.customer_id
		order by o.order_date, o.order_id
	) as amount_change_from_previous
from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- ==============================================================================
-- PROBLEM 5: Compare each order to the next order
-- ==============================================================================

-- LEAD looks forward instead of backward.
-- Useful when you want to know what happened after an event.
select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.order_date,
	o.total_amount,
	LEAD(o.order_date) over (
		partition by c.customer_id
		order by o.order_date, o.order_id
	) as next_order_date,
	LEAD(o.total_amount) over (
		partition by c.customer_id
		order by o.order_date, o.order_id
	) as next_order_amount
from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- ==============================================================================
-- PROBLEM 6: Moving average by customer
-- ==============================================================================

-- This calculates the average of the current order and the two previous orders.
-- ROWS is important: it defines the physical window around the current row.
select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.order_date,
	o.total_amount,
	AVG(o.total_amount) over (
		partition by c.customer_id
		order by o.order_date, o.order_id
		rows between 2 preceding and current row
	) as three_order_moving_avg
from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- ==============================================================================
-- PROBLEM 7: Percent of customer's total spend
-- ==============================================================================

-- SUM as a window function keeps every order row visible while also showing
-- the customer's total spend. GROUP BY would collapse the rows.
select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.total_amount,
	SUM(o.total_amount) over (
		partition by c.customer_id
	) as customer_total_spend,
	ROUND(
		o.total_amount * 100.0 / SUM(o.total_amount) over (
			partition by c.customer_id
		),
		2
	) as percent_of_customer_spend
from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- ==============================================================================
-- PROBLEM 8: Country-level order comparison
-- ==============================================================================

-- Compare each order to the average order amount in the customer's country.
select
	c.country,
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.total_amount,
	AVG(o.total_amount) over (
		partition by c.country
	) as country_avg_order_amount,
	o.total_amount - AVG(o.total_amount) over (
		partition by c.country
	) as difference_from_country_avg
from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- ==============================================================================
-- PROBLEM 9: First and last order values per customer
-- ==============================================================================

-- FIRST_VALUE is straightforward. LAST_VALUE needs a full window frame,
-- otherwise many databases return the current row as the "last" value.
select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.order_date,
	o.total_amount,
	FIRST_VALUE(o.total_amount) over (
		partition by c.customer_id
		order by o.order_date, o.order_id
	) as first_order_amount,
	LAST_VALUE(o.total_amount) over (
		partition by c.customer_id
		order by o.order_date, o.order_id
		rows between unbounded preceding and unbounded following
	) as last_order_amount
from
	customers c
join orders o on
	c.customer_id = o.customer_id;

-- ==============================================================================
-- PROBLEM 10: Customer order counts without collapsing rows
-- ==============================================================================

-- COUNT as a window function gives each row context while preserving detail.
select
	c.customer_id,
	c.customer_name,
	o.order_id,
	o.order_date,
	o.total_amount,
	COUNT(*) over (
		partition by c.customer_id
	) as customer_order_count,
	COUNT(*) over (
		partition by c.country
	) as country_order_count
from
	customers c
join orders o on
	c.customer_id = o.customer_id;
