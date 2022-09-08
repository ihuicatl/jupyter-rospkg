import json


async def test_get_example(jp_fetch):
    # When
    response = await jp_fetch("ros", "get_example")

    # Then
    assert response.code == 200
    payload = json.loads(response.body)
    assert payload == {
        "data": "This is /ros/get_example endpoint!"
    }