from app import create_app, db
from app.models.corent_data import CorentData
from app.models.cast import ApplicationClassification

app = create_app()
with app.app_context():
    corent_count = db.session.query(CorentData).count()
    classification_count = db.session.query(ApplicationClassification).count()
    
    print(f"CorentData: {corent_count}")
    print(f"ApplicationClassification: {classification_count}")
    
    # Check first few app_ids from each
    print("\nFirst 5 CorentData app_ids:")
    corent_apps = db.session.query(CorentData.app_id).limit(5).all()
    for app in corent_apps:
        print(f"  {app.app_id}")
    
    print("\nFirst 5 ApplicationClassification app_ids:")
    class_apps = db.session.query(ApplicationClassification.app_id).limit(5).all()
    for app in class_apps:
        print(f"  {app.app_id}")
