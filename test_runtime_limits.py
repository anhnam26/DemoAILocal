import system_runtime,runtime_limits as limits
from test_app import isolated_db,client

def test_budget_and_config_limits(tmp_path,monkeypatch):
    a=client('admin');s=client('member');monkeypatch.setattr(system_runtime,'CONFIG',tmp_path/'config.json')
    config={**system_runtime.DEFAULT,'parallel':4,'context':8192,'max_tokens':8192}
    assert s.put('/api/admin/system/config',json=config).status_code==403
    assert a.put('/api/admin/system/config',json=config).status_code==200
    b=limits.budget(8192,4,8192)
    assert len(b['slots'])==4 and b['context_total']==32768 and b['effective_output_per_slot']==2048
    assert all(s['max_output']==2048 for s in b['slots'])
    assert a.put('/api/admin/system/config',json={**config,'context':32768}).status_code==400
    assert a.put('/api/admin/system/config',json={**config,'parallel':5}).status_code==422
    assert a.put('/api/admin/system/config',json={**config,'max_tokens':8193}).status_code==422
    args=system_runtime.model_args(config)
    assert args[args.index('--ctx-size')+1]=='32768' and args[args.index('--parallel')+1]=='4'
    assert limits.output_limit(2048,8192)==512
