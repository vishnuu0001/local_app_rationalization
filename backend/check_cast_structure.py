import logging
logging.disable(logging.CRITICAL)

from app import create_app
from app.services.correlation_service import CorrelationService

app = create_app()
with app.app_context():
    cast_data = CorrelationService.get_cast_data()
    
    if cast_data['items_by_app_id']:
        first_app_id = list(cast_data['items_by_app_id'].keys())[0]
        first_item = cast_data['items_by_app_id'][first_app_id]
        
        print('CAST Data Structure:')
        print('=' * 60)
        print('Fields:', list(first_item.keys()))
        print()
        print('Sample values:')
        print(f'  repo field: {repr(first_item.get("repo"))}')
        print(f'  repository field: {repr(first_item.get("repository"))}')
        print(f'  from_app_inventory: {repr(first_item.get("from_app_inventory"))}')
        print(f'  app_name: {first_item.get("app_name")}')
        print()
        print('All CASTData entries have "repo" field (not "repository")!')
