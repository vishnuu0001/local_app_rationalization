"""Utility functions for data processing"""

def calculate_metrics(before_state, after_state):
    """Calculate improvement metrics"""
    metrics = {}
    
    # Calculate cost savings
    if before_state.get('cost') and after_state.get('cost'):
        metrics['cost_savings'] = before_state['cost'] - after_state['cost']
        metrics['cost_savings_percent'] = (metrics['cost_savings'] / before_state['cost']) * 100
    
    # Calculate footprint reduction
    if before_state.get('footprint') and after_state.get('footprint'):
        metrics['footprint_reduction'] = before_state['footprint'] - after_state['footprint']
        metrics['footprint_reduction_percent'] = (metrics['footprint_reduction'] / before_state['footprint']) * 100
    
    # Calculate integration complexity reduction
    if before_state.get('integration_points') and after_state.get('integration_points'):
        complexity_reduction = before_state['integration_points'] - after_state['integration_points']
        metrics['integration_complexity_reduction'] = (complexity_reduction / before_state['integration_points']) * 100
    
    # Calculate cyber risk reduction
    if before_state.get('cyber_risk') and after_state.get('cyber_risk'):
        risk_map = {'Low': 1, 'Medium': 2, 'High': 3}
        before_risk = risk_map.get(before_state['cyber_risk'], 2)
        after_risk = risk_map.get(after_state['cyber_risk'], 2)
        if before_risk > 0:
            metrics['cyber_risk_reduction'] = ((before_risk - after_risk) / before_risk) * 100
    
    return metrics

def match_applications_to_servers(applications, servers):
    """Match applications to servers based on available data"""
    mappings = []
    
    for app in applications:
        for server in servers:
            # Match on server name similarity
            if server.server_name.lower() in app.app_name.lower() or \
               app.app_name.lower() in server.server_name.lower():
                mappings.append({
                    'application': app.app_name,
                    'server': server.server_name,
                    'confidence': 'High'
                })
    
    return mappings

def identify_redundancy(applications):
    """Identify redundant applications"""
    redundancy_groups = {}
    
    for app in applications:
        # Group by capability or function (would be more sophisticated in practice)
        key = app.app_name.split('_')[0] if '_' in app.app_name else app.app_name
        
        if key not in redundancy_groups:
            redundancy_groups[key] = []
        redundancy_groups[key].append(app)
    
    redundant = {k: v for k, v in redundancy_groups.items() if len(v) > 1}
    return redundant
