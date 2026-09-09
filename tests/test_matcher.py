from ownershipos.matcher import build_proposals, score

LOC={"name":"Bellhaven of Maplewood","address":"210 Orchard Lane","city":"Maplewood","state":"OH","zip":"44280","care_offerings":["Assisted Living"],"source_url":"https://example.test/maplewood"}

def test_address_outweighs_rebrand():
    acc={"name":"Old Maplewood Manor","address":"210 Orchard Ln","city":"Maplewood","state":"OH","zip":"44280"}
    total,parts=score(LOC,acc)
    assert total >= 80 and parts["address"] == 100

def test_chow_preserves_old_account():
    parent={"id":"P1","name":"Bellhaven Senior Living","parent_id":None}
    old={"id":"A1","name":"Old Maplewood Manor","address":"210 Orchard Ln","city":"Maplewood","state":"OH","zip":"44280","parent_id":"P0","lifetime_revenue":100,"outstanding_ar":1}
    p=build_proposals([LOC],[parent,old],"P1")
    assert p[0]["kind"].startswith("CHOW")
    assert p[0]["actions"][0]["method"] == "POST_THEN_CHOW"

def test_safe_reparent_without_ar():
    parent={"id":"P1","name":"Bellhaven Senior Living","parent_id":None}
    old={"id":"A1","name":"Old Maplewood Manor","address":"210 Orchard Ln","city":"Maplewood","state":"OH","zip":"44280","parent_id":"P0","lifetime_revenue":100,"outstanding_ar":0}
    p=build_proposals([LOC],[parent,old],"P1")
    assert p[0]["actions"][0]["payload"]["parent_id"] == "P1"
