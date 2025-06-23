SELECT * FROM public.dim_clients
ORDER BY client_id ASC ;

SELECT * FROM public.dim_skus
ORDER BY sku_id ASC ;

SELECT * FROM public.dim_clients
ORDER BY client_id ASC ;

SELECT * FROM public.dim_adjustment_types
ORDER BY adjustment_type_id ASC ;

SELECT * FROM public.dim_keyfigures
ORDER BY key_figure_id ASC ;

SELECT * FROM public.fact_adjustments
ORDER BY client_id ASC, sku_id ASC, client_final_id ASC, period ASC, key_figure_id ASC;

SELECT * FROM public.fact_forecast_stat
ORDER BY client_id ASC, sku_id ASC, client_final_id ASC, period ASC 

SELECT * FROM public.forecast_smoothing_parameters
ORDER BY forecast_run_id ASC

SELECT * FROM public.manual_input_comments
ORDER BY client_id ASC, sku_id ASC, client_final_id ASC, period ASC, key_figure_id ASC ;

SELECT * FROM public.forecast_versions
ORDER BY version_id ASC ;

SELECT * FROM public.fact_forecast_versioned
ORDER BY version_id ASC, client_id ASC, sku_id ASC, client_final_id ASC, period ASC, key_figure_id ASC ;

SELECT * FROM public.fact_history
ORDER BY client_id ASC, sku_id ASC, client_final_id ASC, period ASC, key_figure_id ASC ;