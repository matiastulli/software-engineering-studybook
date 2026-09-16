/*
SQL KEY CONCEPTS - SHORT EXERCISE SET

Use the same tables from sql_crud.sql:
- customers(customer_id, customer_name, email, signup_date, country)
- orders(order_id, customer_id, order_date, total_amount)
- order_items(item_id, order_id, product_id, quantity, unit_price)

Goal: write each query yourself. Keep the solutions simple.
*/

-- ==============================================================================
-- EXERCISE 1: Customers with their orders
-- ==============================================================================

-- Show customer_id, customer_name, order_id, order_date, and total_amount.
-- Include only customers who have placed orders.

select
	c.customer_id,
	customer_name,
	order_id,
	order_date,
	total_amount
from
	customers c
inner join orders o 
on c.customer_id = o.customer_id 

-- ==============================================================================
-- EXERCISE 2: Total spend per customer
-- ==============================================================================

-- Show each customer's customer_id, customer_name, and total_spend.
-- Include customers with no orders and show their total_spend as 0.

select
	c.customer_id,
	customer_name,
	coalesce(sum(total_amount), 0) as total_spend
from
	customers c
left join orders o 
on
	c.customer_id = o.customer_id
group by
	c.customer_id,
	customer_name

-- ==============================================================================
-- EXERCISE 3: Customers with no orders
-- ==============================================================================

-- Find customers who have never placed an order.
-- Practice using NOT EXISTS.

select
	*
from
	customers c
where
	not exists (
	select
		o2.customer_id
	from
		orders o2
	where
		c.customer_id = o2.customer_id )

-- ==============================================================================
-- EXERCISE 4: Orders above the average order amount
-- ==============================================================================

-- Show orders where total_amount is greater than the average total_amount
-- across all orders.
-- Practice using a scalar subquery.

select
	order_id
from
	orders o 
where o.total_amount > (
select
	avg(total_amount) as avg_amount
from
	orders )

-- ==============================================================================
-- EXERCISE 5: Customers who spent more than 200
-- ==============================================================================

-- Show customer_id and customer_name for customers whose total order spend
-- is greater than 200.
-- Practice GROUP BY + HAVING inside a subquery.

select
	c.customer_id,
	customer_name
from
	customers c
inner join orders o on
	c.customer_id = o.customer_id
group by
	c.customer_id,
	customer_name
having
	sum(total_amount) > 200


-- ==============================================================================
-- EXERCISE 6: Latest order per customer
-- ==============================================================================

-- Show the latest order for each customer who has placed an order.
-- Practice ROW_NUMBER with PARTITION BY customer_id.

with my_ets as (
select
	c.customer_id,
	customer_name,
	o.order_id,
	o.order_date,
	row_number() over (partition by o.customer_id
order by
	o.order_date desc ) as rnumber
from
	customers c
inner join orders o on
	c.customer_id = o.customer_id)
select
	*
from
	my_ets
where
	rnumber = 1


-- ==============================================================================
-- EXERCISE 7: Running total per customer
-- ==============================================================================

-- Show each order with a running total of total_amount for that customer,
-- ordered by order_date.
-- Practice SUM(...) OVER (...).

select
	o.order_id,
	o.order_date,
	o.total_amount,
	SUM(o.total_amount) over (partition by o.customer_id order by o.order_date) as running_total
from
	orders o;

-- ==============================================================================
-- EXERCISE 8: Compare order to previous order
-- ==============================================================================

-- Show each order with the previous_order_amount for the same customer.
-- Also show amount_change_from_previous.
-- Practice LAG.


-- ==============================================================================
-- EXERCISE 9: Rank customer orders by amount
-- ==============================================================================

-- For each customer, rank their orders from highest total_amount to lowest.
-- Show customer_id, order_id, total_amount, and amount_rank.
-- Practice RANK or DENSE_RANK.

select
    customer_id,
    order_id,
    total_amount,
    rank() over (partition by customer_id order by total_amount desc) as amount_rank
from
    orders;


-- ==============================================================================
-- EXERCISE 10: Orders with more than 3 total items
-- ==============================================================================

-- Show order_id, customer_id, order_date, and total_amount for orders where
-- the sum of item quantity is greater than 3.
-- Practice a subquery using order_items.

