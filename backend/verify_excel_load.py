"""Verify Excel data loaded correctly"""
from app import db, create_app

app = create_app()
with app.app_context():
    from app.models.corent_data import CorentData
    from app.models.cast import CASTData
    
    corent_count = CorentData.query.count()
    cast_count = CASTData.query.count()
    
    print("=" * 80)
    print("DATABASE VERIFICATION AFTER EXCEL LOAD")
    print("=" * 80)
    print(f"CORENT Records: {corent_count}")
    print(f"CAST Records: {cast_count}")
    
    # Count unique servers
    corent = CorentData.query.all()
    unique_hosts = set(c.platform_host for c in corent if c.platform_host)
    
    print(f"\nUnique Platform Hosts: {len(unique_hosts)}")
    print("\nTop 20 Host Distribution:")
    host_counts = {}
    for c in corent:
        if c.platform_host:
            host_counts[c.platform_host] = host_counts.get(c.platform_host, 0) + 1
    
    for host, count in sorted(host_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {host: <30} -> {count} app(s)")
    
    print("=" * 80)
