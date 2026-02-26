"""Debug script to analyze server data"""
from app import db, create_app

app = create_app()
with app.app_context():
    from app.models.corent_data import CorentData
    
    corent = CorentData.query.all()
    print(f"Total Corent Records: {len(corent)}\n")
    
    print("All platform_host values by app:")
    print("-" * 60)
    for item in corent:
        print(f"  {item.app_id: <10} -> Platform: {item.platform_host}")
    
    unique_hosts = set(c.platform_host for c in corent if c.platform_host)
    print(f"\nUnique platform_host values: {len(unique_hosts)}")
    print("-" * 60)
    for host in sorted(unique_hosts):
        apps = [c.app_id for c in corent if c.platform_host == host]
        print(f"  {host: <20} -> {len(apps)} app(s): {', '.join(apps)}")
    
    # Check for NULL or empty platform_host
    null_hosts = [c.app_id for c in corent if not c.platform_host]
    if null_hosts:
        print(f"\nApps with NULL/empty platform_host: {null_hosts}")
