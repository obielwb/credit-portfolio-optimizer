"""Branch-and-Bound credit-limit optimization with an operational limit floor."""

import heapq
import numpy as np

from models import Client, ModelParameters
from evaluation import (
    calculate_max_client_limit,
    evaluate_client_profitability,
    client_fails_business_filter,
    approved_limit_floor,
)
from progress import notify_progress

def solve_lp_relaxation(clients: list[Client], parameters: ModelParameters, bounds: list[tuple[float, float]]) -> tuple[float, list[float]]:
    """Solve the continuous relaxation as a fractional-knapsack problem.

    This is exact for the model's continuous relaxation and runs in
    ``O(N log N)``. It returns ``(-inf, [])`` for an infeasible node.
    """
    n = len(clients)
    L = [0.0] * n
    
    c = []
    w = []
    for client in clients:

        unit_metrics = evaluate_client_profitability(1.0, client, parameters)
        risk_weight = unit_metrics.expected_loss - parameters.baseline_default_rate
        c.append(unit_metrics.expected_return)
        w.append(risk_weight)

    for i in range(n):
        lb, ub = bounds[i]
        if lb > ub:
            return -np.inf, []
            
    total_profit = 0.0
    accumulated_risk = 0.0
    

    for i in range(n):
        lb, ub = bounds[i]
        L[i] = lb
        total_profit += c[i] * lb
        accumulated_risk += w[i] * lb
        
    candidates = []
    for i in range(n):
        lb, ub = bounds[i]
        remaining_capacity = ub - lb
        
        if remaining_capacity <= 1e-9:
            continue
        if c[i] <= 0:
            continue
            
        if w[i] <= 0:

            L[i] += remaining_capacity
            total_profit += c[i] * remaining_capacity
            accumulated_risk += w[i] * remaining_capacity
        else:

            efficiency = c[i] / w[i]
            candidates.append((efficiency, i, remaining_capacity))
            
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    for efficiency, i, remaining_capacity in candidates:
        risk_margin = -accumulated_risk
        if risk_margin <= 1e-9:
            break
            
        delta = min(remaining_capacity, risk_margin / w[i])
        L[i] += delta
        total_profit += c[i] * delta
        accumulated_risk += w[i] * delta
        

    if accumulated_risk > 1e-5:
        return -np.inf, []
        
    return total_profit, L


def optimize_branch_and_bound(clients: list[Client], parameters: ModelParameters) -> list[float]:
    """Optimize globally while preventing positive limits below the configured floor."""
    n = len(clients)
    L_min = approved_limit_floor(parameters)

    notify_progress("calculating_constraints")
    

    initial_bounds = []
    for client in clients:
        ceiling = calculate_max_client_limit(client, parameters)
        expected_return = evaluate_client_profitability(1.0, client, parameters).expected_return
        if expected_return <= 0 or ceiling < L_min or client_fails_business_filter(client, parameters):
            initial_bounds.append((0.0, 0.0))
        else:
            initial_bounds.append((0.0, ceiling))
            

    best_profit = -np.inf
    best_L = None
    
    pq = []
    
    root_profit, L_raiz = solve_lp_relaxation(clients, parameters, initial_bounds)
    if root_profit == -np.inf:
        return [0.0] * n 
        

    heapq.heappush(pq, (-root_profit, 0, initial_bounds, L_raiz))

    notify_progress("tableau_calculation")
    
    iterations = 0
    MAX_ITER = 50000
    first_iteration = True
    
    while pq and iterations < MAX_ITER:
        if first_iteration:
            notify_progress("generating_recommendations")
            first_iteration = False
        iterations += 1
        negative_profit, level, bounds, L = heapq.heappop(pq)
        relaxed_profit = -negative_profit
        

        if relaxed_profit <= best_profit + 1e-5:
            continue
            
        is_integer = True
        branch_idx = -1
        

        for i in range(n):
            if 1e-5 < L[i] < L_min - 1e-5:
                is_integer = False
                branch_idx = i
                break
                
        if is_integer:

            if relaxed_profit > best_profit:
                best_profit = relaxed_profit
                best_L = L
            continue
            

        bounds_zero = list(bounds)
        bounds_zero[branch_idx] = (0.0, 0.0)
        zero_profit, L_zero = solve_lp_relaxation(clients, parameters, bounds_zero)
        if zero_profit > best_profit:
            heapq.heappush(pq, (-zero_profit, level + 1, bounds_zero, L_zero))
            

        ceiling = bounds[branch_idx][1]
        if ceiling >= L_min:
            bounds_min = list(bounds)
            bounds_min[branch_idx] = (L_min, ceiling)
            min_profit, L_min_sol = solve_lp_relaxation(clients, parameters, bounds_min)
            if min_profit > best_profit:
                heapq.heappush(pq, (-min_profit, level + 1, bounds_min, L_min_sol))
                
    if best_L is None:
        return [0.0] * n

    notify_progress("validating_constraints")
        
    return best_L
