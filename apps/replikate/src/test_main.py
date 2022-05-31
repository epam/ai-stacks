import src.main as main

def test_merge():
  a1   = {}
  d1 = main.deep_merge(a1, {"a": "1", "b": "2"})
  assert a1 == {"a": "1", "b": "2"}
  assert d1 == {"a": "1", "b": "2"}

  a2 = {"a": "1", "c": "3"}
  d2 = main.deep_merge(a2, {"a": "1", "b": "2"})
  assert a2 == {"a": "1", "b": "2", "c": "3"}
  assert d2["b"] == {"b": 2}

  a3 = {"a": "1"}
  d3 = main.deep_merge(a3, {"a": "5", "b": "2"})
  assert a3 == {"a": "1", "b": "2"}
  assert d3 == {"b": "2"}

def test_quota():
  spec11 = {
    "resourceQuotaSpec": {
      "hard": {
          "cpu": "12",
      }
    }
  }
  spec12 = {
    "resourceQuotaSpec": {
        "hard": {
            "cpu": "8",
            "memory": "16Gi",
        }
    }
  }
  d1 = main.deep_merge(spec11, spec12)
  assert spec11["resourceQuotaSpec"]["hard"]["cpu"] == "12"
  assert spec11["resourceQuotaSpec"]["hard"]["memory"] == "16Gi"
  assert d1 == {}

  spec21 = {
      "resourceQuotaSpec": {
          "hard": {
              "cpu": "30",
              "memory": "60Gi"
          }
      }
  }
  d2 = main.deep_merge(spec21, main.DEFAULT_SPEC)
  assert spec21["resourceQuotaSpec"]["hard"]["cpu"] == "30"
  assert spec21["resourceQuotaSpec"]["hard"]["memory"] == "60Gi"
  assert d2 == {}


def test_merge_lists():
  s1 = [1, 2, 3]
  d1 = main.merge_list(s1, [2, 3, 4])
  assert s1 == [1, 2, 3, 4]
  assert d1 == [4]
