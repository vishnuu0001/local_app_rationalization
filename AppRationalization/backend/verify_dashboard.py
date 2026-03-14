"""Verify dashboard data with actual production data"""
from app import db, create_app
from app.services.insight_service import InsightService

app = create_app()
with app.app_context():
    insights = InsightService.get_dashboard_insights()
    
    print("=" * 80)
    print("DASHBOARD INSIGHTS - PRODUCTION DATA")
    print("=" * 80)
    
    summary = insights['summary']
    print(f"\nSUMMARY METRICS:")
    print(f"  Total Applications: {summary['total_applications']}")
    print(f"  Total Servers: {summary['total_servers']}")
    print(f"  Cloud Ready (%): {summary['cloud_readiness_percentage']:.1f}%")
    print(f"  Average Risk Score: {summary['average_risk_score']:.2f}")
    
    print(f"\nINFRASTRUCTURE ANALYSIS:")
    infra = insights['infrastructure_insights']
    print(f"  On-Premise Apps: {infra.get('on_premise_count', 0)}")
    print(f"  Cloud Apps: {infra.get('cloud_count', 0)}")
    print(f"  Hybrid Apps: {infra.get('hybrid_count', 0)}")
    
    print(f"\nCODE ANALYSIS:")
    code = insights['code_analysis']
    print(f"  Available Code Analysis: {code.get('with_source_code', 0)} apps")
    print(f"  High Risk Code: {code.get('high_risk_count', 0)} apps")
    
    print("\n" + "=" * 80)
