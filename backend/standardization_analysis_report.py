"""Verify standardization analysis with production data"""
from app import db, create_app
from app.services.standardization_analysis_service import StandardizationAnalysisService

app = create_app()
with app.app_context():
    analysis = StandardizationAnalysisService.analyze_all_data()
    
    print("=" * 100)
    print("STANDARDIZATION & CONSOLIDATION ANALYSIS - BASED ON ACTUAL CORENT & CAST DATA")
    print("=" * 100)
    
    # Infrastructure Analysis
    print("\n[1] INFRASTRUCTURE ANALYSIS")
    print("-" * 100)
    infra = analysis['infrastructure_analysis']
    print(f"  Total Unique Servers: {infra['total_servers']}")
    print(f"  Environment Distribution: {infra['environment_distribution']}")
    print(f"  Cloud Readiness Breakdown:")
    for suit, count in infra['cloud_readiness'].items():
        print(f"    - {suit}: {count} applications")
    print(f"\n  Top 5 Servers by App Count:")
    for i, (server, data) in enumerate(infra['top_servers'][:5], 1):
        print(f"    {i}. {server}: {len(data['apps'])} applications")
    
    # Code Analysis
    print("\n[2] CODE ANALYSIS")
    print("-" * 100)
    code = analysis['code_analysis']
    print(f"  Total Applications: {code['total_with_source_code'] + code['total_without_source_code']}")
    print(f"  With Source Code: {code['total_with_source_code']} ({code['source_code_availability']})")
    print(f"  Without Source Code: {code['total_without_source_code']}")
    print(f"  Cloud Ready Applications: {code['cloud_ready_apps']} ({code['cloud_readiness_percentage']})")
    print(f"\n  Top Programming Languages:")
    for lang, count in list(code['top_languages'].items())[:5]:
        print(f"    - {lang}: {count} apps")
    print(f"\n  Architecture Distribution:")
    for arch, count in sorted(code['architecture_distribution'].items(), key=lambda x: -x[1])[:5]:
        print(f"    - {arch}: {count} apps")
    
    # Technology Standardization
    print("\n[3] TECHNOLOGY STANDARDIZATION OPPORTUNITIES")
    print("-" * 100)
    tech = analysis['technology_standardization']
    print(f"  Operating Systems (Top 5):")
    for os, count in list(tech['operating_systems'].items())[:5]:
        print(f"    - {os}: {count} apps")
    print(f"\n  Database Engines (Top 5):")
    for db, count in list(tech['database_engines'].items())[:5]:
        print(f"    - {db}: {count} apps")
    print(f"\n  Server Types (Top 5):")
    for st, count in list(tech['server_types'].items())[:5]:
        print(f"    - {st}: {count} apps")
    print(f"\n  Apps Ready for Standardization: {tech['standardization_potential']}")
    
    # Consolidation Opportunities
    print("\n[4] CONSOLIDATION OPPORTUNITIES (Top 5)")
    print("-" * 100)
    for i, opp in enumerate(analysis['consolidation_opportunities'], 1):
        print(f"  {i}. Platform: {opp['platform']}")
        print(f"     Total Apps: {opp['total_apps']} | Stable: {opp['stable_apps']} | Unstable: {opp['unstable_apps']}")
        print(f"     Consolidation Potential: {opp['potential_consolidation']} applications")
        print(f"     Reason: {opp['reason']}\n")
    
    # Business Value Recommendations
    print("\n[5] BUSINESS VALUE RECOMMENDATIONS")
    print("-" * 100)
    for i, rec in enumerate(analysis['business_value_recommendations'], 1):
        print(f"  {i}. [{rec['priority']}] {rec['title']}")
        print(f"     Category: {rec['category']}")
        print(f"     Value Proposition: {rec['value_proposition']}")
        print(f"     Business Impact: {rec['business_impact']}")
        print(f"     Estimated Annual Savings: {rec['estimated_savings']}")
        print(f"     Timeline: {rec['timeline']}\n")
    
    # ROI Analysis
    print("\n[6] ROI ANALYSIS FOR STANDARDIZATION & CONSOLIDATION")
    print("-" * 100)
    roi = analysis['roi_analysis']
    print(f"  Current Annual Cost: {roi['current_annual_cost']}")
    print(f"    - Infrastructure: {roi['infrastructure_cost']}")
    print(f"    - Management: {roi['management_cost']}")
    print(f"    - Licensing: {roi['license_cost']}")
    print(f"\n  Post-Standardization Annual Cost: {roi['post_standardization_cost']}")
    print(f"  Annual Savings: {roi['annual_savings']}")
    print(f"  Implementation Cost: {roi['implementation_cost']}")
    print(f"  Payback Period: {roi['payback_period_years']} years")
    print(f"  5-Year ROI: {roi['five_year_roi']}")
    print(f"  ROI Percentage: {roi['roi_percentage']}")
    
    # Risk Assessment
    print("\n[7] CONSOLIDATION RISK ASSESSMENT")
    print("-" * 100)
    for i, risk in enumerate(analysis['risk_assessment'], 1):
        print(f"  {i}. [{risk['level']}] {risk['category']}")
        print(f"     Description: {risk['description']}")
        print(f"     Apps Affected: {risk['apps_affected']}")
        print(f"     Mitigation: {risk['mitigation']}\n")
    
    print("=" * 100)
    print("END OF ANALYSIS REPORT")
    print("=" * 100)
