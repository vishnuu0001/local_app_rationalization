"""
Populate ApplicationClassification table with test data for capability mapping
"""
from app import create_app, db
from app.models.corent_data import CorentData
from app.models.cast import CASTAnalysis, ApplicationClassification

# Sample business capabilities to assign
capabilities = [
    "Financial Processing",
    "Reporting & Analytics", 
    "Data Management",
    "Workflow Management",
    "Integration",
    "User Management",
    "Security Monitoring"
]

app = create_app()
with app.app_context():
    # First, create a parent CASTAnalysis record if it doesn't exist
    cast_analysis = db.session.query(CASTAnalysis).first()
    if not cast_analysis:
        cast_analysis = CASTAnalysis(
            file_id="test-cast-001",
            filename="test_cast_data.xlsx",
            file_path="/test/test_cast_data.xlsx"
        )
        db.session.add(cast_analysis)
        db.session.flush()  # Flush to get the ID without committing
        print(f"Created CASTAnalysis record with ID: {cast_analysis.id}")
    else:
        print(f"Using existing CASTAnalysis record with ID: {cast_analysis.id}")
    
    # Get all CORENT applications
    corent_apps = db.session.query(CorentData).all()
    
    print(f"Creating ApplicationClassification records for {len(corent_apps)} applications...")
    
    # Assign capabilities strategically to create consolidation opportunities
    for idx, corent_app in enumerate(corent_apps):
        # Assign multiple apps to same capabilities to create consolidation candidates
        capability_idx = (idx // 3) % len(capabilities)  # Every 3 apps get same capability
        capability = capabilities[capability_idx]
        app_type = "Web Application" if idx % 2 == 0 else "Backend Service"
        
        classification = ApplicationClassification(
            cast_analysis_id=cast_analysis.id,
            app_id=corent_app.app_id,
            application=corent_app.app_name,
            application_type=app_type,
            install_type=corent_app.install_type or "Unknown",
            capabilities=capability
        )
        
        db.session.add(classification)
        
        if (idx + 1) % 30 == 0:
            print(f"  Added {idx + 1} records...")
    
    db.session.commit()
    print(f"Successfully created ApplicationClassification records!")
    
    # Verify
    total = db.session.query(ApplicationClassification).count()
    print(f"Total ApplicationClassification records now: {total}")
    
    # Show sample data
    print(f"\nCapabilities by count:")
    from sqlalchemy import func
    capability_counts = db.session.query(
        ApplicationClassification.capabilities,
        func.count(ApplicationClassification.id).label('count')
    ).group_by(ApplicationClassification.capabilities).all()
    
    for cap, count in capability_counts:
        candidates = "CONSOLIDATION CANDIDATE" if count > 1 else "singleton"
        print(f"  {cap}: {count} applications ({candidates})")
