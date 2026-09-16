-- ==============================================================================
-- PROBLEM 2: Customers who have placed at least one order
-- ==============================================================================

-- IN checks if the customer_id exists in the result of the subquery.
-- This is useful when the filtering condition lives in another table.
select
	c.customer_id,
	c.customer_name,
	c.email
from
	customers c
where
	c.customer_id in (
		select
			o.customer_id
		from
			orders o
	);

-- ==============================================================================
-- PROBLEM 3: Customers who have never placed an order
-- ==============================================================================

-- NOT EXISTS is usually safer than NOT IN when the subquery could return NULLs.
select
	c.customer_id,
	c.customer_name,
	c.email
from
	customers c
where
	not exists (
		select
			1
		from
			orders o
		where
			o.customer_id = c.customer_id
	);

-- ==============================================================================
-- PROBLEM 4: Orders above the overall average order amount
-- ==============================================================================

-- This scalar subquery returns one value: the average order amount.
select
	o.order_id,
	o.customer_id,
	o.order_date,
	o.total_amount
from
	orders o
where
	o.total_amount > (
		select
			AVG(total_amount)
		from
			orders
	);

-- ==============================================================================
-- PROBLEM 5: Orders above each customer's average order amount
-- ==============================================================================

-- This is a correlated subquery because the inner query references the outer row.
-- Por cada order, comparo contra el promedio de ese mismo customer.
select
	o.order_id,
	o.customer_id,
	o.order_date,
	o.total_amount
from
	orders o
where
	o.total_amount > (
		select
			AVG(o2.total_amount)
		from
			orders o2
		where
			o2.customer_id = o.customer_id
	);

-- ==============================================================================
-- PROBLEM 6: Customers with total spend greater than 1000
-- ==============================================================================

-- The subquery groups orders by customer and returns only high-value customers.
select
	c.customer_id,
	c.customer_name,
	c.country
from
	customers c
where
	c.customer_id in (
		select
			o.customer_id
		from
			orders o
		group by
			o.customer_id
		having
			SUM(o.total_amount) > 1000
	);

-- ==============================================================================
-- PROBLEM 7: Show each customer with their total spend
-- ==============================================================================

-- A subquery in the SELECT list can calculate a value for each row.
-- COALESCE returns 0 for customers with no orders.
select
	c.customer_id,
	c.customer_name,
	COALESCE(
		(
			select
				SUM(o.total_amount)
			from
				orders o
			where
				o.customer_id = c.customer_id
		),
		0
	) as total_spend
from
	customers c;

-- ==============================================================================
-- PROBLEM 8: Latest order for each customer
-- ==============================================================================

-- The subquery gets the most recent order date for the current customer.
-- If a customer has multiple orders on the same latest date, this can return ties.
select
	o.order_id,
	o.customer_id,
	o.order_date,
	o.total_amount
from
	orders o
where
	o.order_date = (
		select
			MAX(o2.order_date)
		from
			orders o2
		where
			o2.customer_id = o.customer_id
	);

-- ==============================================================================
-- PROBLEM 9: Most expensive order item per order
-- ==============================================================================

-- This finds the item or items with the highest unit price inside each order.
select
	oi.order_id,
	oi.item_id,
	oi.product_id,
	oi.quantity,
	oi.unit_price
from
	order_items oi
where
	oi.unit_price = (
		select
			MAX(oi2.unit_price)
		from
			order_items oi2
		where
			oi2.order_id = oi.order_id
	);

-- ==============================================================================
-- PROBLEM 10: Orders that include more than 3 total items
-- ==============================================================================

-- This subquery filters orders based on aggregated order_items data.
select
	o.order_id,
	o.customer_id,
	o.order_date,
	o.total_amount
from
	orders o
where
	o.order_id in (
		select
			oi.order_id
		from
			order_items oi
		group by
			oi.order_id
		having
			SUM(oi.quantity) > 3
	);

-- ==============================================================================
-- PROBLEM 11: Customers from countries with more than 5 customers
-- ==============================================================================

-- The subquery identifies countries that meet the condition first.
select
	c.customer_id,
	c.customer_name,
	c.country
from
	customers c
where
	c.country in (
		select
			c2.country
		from
			customers c2
		group by
			c2.country
		having
			COUNT(*) > 5
	);

-- ==============================================================================
-- PROBLEM 12: Derived table for customer totals
-- ==============================================================================

-- A subquery in FROM is called a derived table.
-- This is helpful when you want to calculate totals first, then filter or sort.
select
	customer_totals.customer_id,
	customer_totals.total_spend,
	customer_totals.order_count
from
	(
		select
			o.customer_id,
			SUM(o.total_amount) as total_spend,
			COUNT(*) as order_count
		from
			orders o
		group by
			o.customer_id
	) customer_totals
where
	customer_totals.order_count >= 2
order by
	customer_totals.total_spend desc;

-- ==============================================================================
-- PROBLEM 13: Customers whose total spend is above the customer average
-- ==============================================================================

-- First calculate total spend per customer, then compare those totals to
-- the average customer total spend.
select
	customer_totals.customer_id,
	customer_totals.total_spend
from
	(
		select
			o.customer_id,
			SUM(o.total_amount) as total_spend
		from
			orders o
		group by
			o.customer_id
	) customer_totals
where
	customer_totals.total_spend > (
		select
			AVG(all_totals.total_spend)
		from
			(
				select
					o.customer_id,
					SUM(o.total_amount) as total_spend
				from
					orders o
				group by
					o.customer_id
			) all_totals
	);

-- ==============================================================================
-- PROBLEM 14: EXISTS vs JOIN style question
-- ==============================================================================

-- EXISTS checks whether at least one matching row exists.
-- It does not need to return data from the inner query.
select
	c.customer_id,
	c.customer_name
from
	customers c
where
	exists (
		select
			1
		from
			orders o
		where
			o.customer_id = c.customer_id
			and o.total_amount >= 500
	);

-- ==============================================================================
-- PROBLEM 15: Products that appear in multiple orders
-- ==============================================================================

-- This uses order_items as the source and filters products by order count.
select
	oi.product_id
from
	order_items oi
where
	oi.product_id in (
		select
			oi2.product_id
		from
			order_items oi2
		group by
			oi2.product_id
		having
			COUNT(distinct oi2.order_id) > 1
	)
group by
	oi.product_id;
