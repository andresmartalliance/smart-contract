from .test_workflow import flow

def auth(token,user,tenant):
    return {'Authorization': f'Bearer {token(user,tenant)}'}

def test_cross_tenant_isolation(testing):
    client,token=testing
    payload={'workflow': flow(4).model_dump(mode='json')}
    r=client.post('/api/v1/workflows',json=payload,headers=auth(token,'alice','tenant-a'))
    assert r.status_code==201, r.text
    workflow_id=r.json()['id']
    a=client.get('/api/v1/workflows',headers=auth(token,'alice','tenant-a'))
    b=client.get('/api/v1/workflows',headers=auth(token,'charlie','tenant-b'))
    assert len(a.json())==1 and b.json()==[]
    cross=client.get(f'/api/v1/workflows/{workflow_id}',headers=auth(token,'charlie','tenant-b'))
    assert cross.status_code==404

def test_operator_cannot_create_flow(testing):
    client,token=testing
    result=client.post('/api/v1/workflows',json={'workflow':flow().model_dump(mode='json')},headers=auth(token,'bob','tenant-b'))
    assert result.status_code==403

def test_user_claims_do_not_bypass_membership(testing):
    client,token=testing
    result=client.get('/api/v1/workflows',headers=auth(token,'alice','tenant-b'))
    assert result.status_code==403

def test_maira_is_not_faked_as_ready(testing):
    client,token=testing
    r=client.get('/api/v1/maira/capabilities',headers=auth(token,'alice','tenant-a'))
    assert r.status_code==200
    assert r.json()['status']=='NOT_CONFIGURED'
    assert r.json()['executable_actions_enabled'] is False
