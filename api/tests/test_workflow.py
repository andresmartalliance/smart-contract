from app.workflow.schema import WorkflowDefinition
from app.workflow.validator import topological_order, WorkflowInvalid
from app.workflow.simulator import simulate
from app.workflow.rules import evaluate
from app.workflow.schema import Condition
import pytest

def flow(n=4):
    nodes = [{'id':'start', 'label':'Start','kind':'START'}]
    nodes += [{'id':f's{i}', 'label':f'Paso {i}', 'kind':'APPROVAL', 'role':'JURIDICO'} for i in range(n)]
    nodes += [{'id':'end', 'label':'End','kind':'END'}]
    ids = [x['id'] for x in nodes]
    return WorkflowDefinition(key='generic',name='Generic',modality_key='any_future_modality',
      nodes=nodes, edges=[{'source':ids[i], 'target':ids[i+1]} for i in range(len(ids)-1)])

def test_128_steps_without_fixed_modality():
    wf = flow(128)
    ordered = topological_order(wf)
    assert len(ordered) == 130
    assert ordered[1]=='s0' and ordered[-2]=='s127'

def test_cycle_rejected():
    wf = flow()
    wf.edges.append(type(wf.edges[0])(source='s3', target='s1'))
    with pytest.raises(WorkflowInvalid, match='Cyclic'):topological_order(wf)

def test_protected_disabled_rejected():
    wf = flow()
    wf.nodes[1].policy='LEGAL_LOCKED'
    wf.nodes[1].enabled=False
    with pytest.raises(WorkflowInvalid, match='Protected'):topological_order(wf)

def test_unknown_rule_does_not_pass():
    assert evaluate(Condition(field='contract.amount',op='gte',value=100),{}) is None
    assert evaluate(Condition(field='contract.amount',op='gte',value=100),{'contract':{'amount':120}}) is True

def test_simulation_requires_completed_deps():
    wf = flow(2)
    result=simulate(wf,{},set())
    assert result['start']=='AVAILABLE'
    assert result['s0']=='WAITING_DEPENDENCIES'
    result=simulate(wf,{}, {'start'})
    assert result['s0']=='AVAILABLE'
