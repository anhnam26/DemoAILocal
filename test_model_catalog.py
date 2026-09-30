import model_provider


def test_numeric_slots_aliases_duplicates_empty_and_conflicts(monkeypatch):
    monkeypatch.setattr(model_provider.config,'env',lambda:dict(MODEL='a',MODEL10='z',MODEL2='b',MODEL_3='b',OPENROUTER_MODEL4='c',MODEL4='conflict',MODEL5=' ',API_KEY='secret',MODEL_LABEL='ignored'))
    c=model_provider.catalog()
    assert model_provider.models()==['a','b','z']
    assert c['items'][1]['slots']==['MODEL2','MODEL3']
    assert c['warnings']==[dict(slot='MODEL4',variables=['MODEL4','OPENROUTER_MODEL4'],reason='conflicting_aliases')]
    assert 'secret' not in str(c)


def test_primary_compatibility_and_dynamic_changes(monkeypatch):
    values=dict(MODEL='old',OPENROUTER_MODEL='override',MODEL2='second')
    monkeypatch.setattr(model_provider.config,'env',lambda:values)
    assert model_provider.models()==['override','second']
    assert model_provider.catalog()['warnings'][0]['reason']=='primary_override'
    values['MODEL1']='new';assert model_provider.models()==['override','new','second']
    values.pop('MODEL2');assert 'second' not in model_provider.models()
