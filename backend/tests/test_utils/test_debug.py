"""
Tests for debug utils: build_var_tree (injected into debuggee).
We exec the tree-building source and assert tree shape; no Docker/pdb required.
"""

from utils.debug_tree_source import BUILD_VAR_TREE_SOURCE


def _get_build_var_tree():
    ns = {}
    exec(BUILD_VAR_TREE_SOURCE, ns)
    return ns["build_var_tree"]


class TestBuildVarTree:
    """Test the tree-building logic (same code injected into debuggee)."""

    def test_primitives(self):
        build_var_tree = _get_build_var_tree()
        tree = build_var_tree({"x": 1, "y": "hi", "z": None})
        assert len(tree) == 3
        for name in ("x", "y", "z"):
            assert "id" in tree[name] and "repr_tree" in tree[name]
        n = tree["x"]["repr_tree"]
        assert n["name"] == "x" and n["value"] == "1" and n["kind"] == "primitive"
        assert tree["y"]["repr_tree"]["value"] == "'hi'" and tree["y"]["repr_tree"]["kind"] == "primitive"
        assert tree["z"]["repr_tree"]["value"] == "None" and tree["z"]["repr_tree"]["kind"] == "primitive"

    def test_filters_dunder(self):
        build_var_tree = _get_build_var_tree()
        tree = build_var_tree({"__name__": "x", "a": 1})
        assert len(tree) == 1
        assert "a" in tree and tree["a"]["repr_tree"]["name"] == "a"

    def test_list_children(self):
        build_var_tree = _get_build_var_tree()
        tree = build_var_tree({"lst": [10, 20, 30]})
        assert len(tree) == 1
        node = tree["lst"]["repr_tree"]
        assert node["kind"] == "list"
        assert "children" in node
        assert len(node["children"]) == 3
        assert (
            node["children"][0]["name"] == "0" and node["children"][0]["value"] == "10"
        )
        assert node["children"][1]["value"] == "20"
        assert node["children"][2]["value"] == "30"

    def test_dict_children(self):
        build_var_tree = _get_build_var_tree()
        tree = build_var_tree({"d": {"a": 1, "b": 2}})
        assert len(tree) == 1
        node = tree["d"]["repr_tree"]
        assert node["kind"] == "dict"
        by_name = {n["name"]: n for n in node["children"]}
        assert by_name["a"]["value"] == "1"
        assert by_name["b"]["value"] == "2"

    def test_instance_attributes(self):
        build_var_tree = _get_build_var_tree()

        class C:
            def __init__(self):
                self.x = 42
                self.name = "foo"

        tree = build_var_tree({"obj": C()})
        assert len(tree) == 1
        node = tree["obj"]["repr_tree"]
        assert node["kind"] == "instance"
        by_name = {n["name"]: n for n in node["children"]}
        assert by_name["x"]["value"] == "42"
        assert by_name["name"]["value"] == "'foo'"

    def test_cycle(self):
        build_var_tree = _get_build_var_tree()
        lst = [1, 2]
        lst.append(lst)
        tree = build_var_tree({"lst": lst})
        assert len(tree) == 1
        node = tree["lst"]["repr_tree"]
        assert node["kind"] == "list"
        assert len(node["children"]) == 3
        assert node["children"][2]["value"] == "<cycle>"

    def test_max_children_truncation(self):
        build_var_tree = _get_build_var_tree()
        tree = build_var_tree({"lst": list(range(100))}, max_children=5)
        assert len(tree) == 1
        children = tree["lst"]["repr_tree"]["children"]
        assert len(children) == 6  # 5 items + "... N more"
        assert children[5]["value"] == "95 more"

    def test_max_depth(self):
        build_var_tree = _get_build_var_tree()
        # Nest list 3 levels; with max_depth=2, we expand at depth 0,1,2; depth 3 is primitive
        tree = build_var_tree({"a": [[[1, 2]]]}, max_depth=2)
        assert len(tree) == 1
        node = tree["a"]["repr_tree"]
        assert node["kind"] == "list"
        inner = node["children"][0]
        assert inner["kind"] == "list"
        inner2 = inner["children"][0]
        # [1, 2] is at depth 2 so still expanded; its children (1, 2) are at depth 3 -> primitive
        assert inner2["kind"] == "list"
        assert len(inner2["children"]) == 2
        assert (
            inner2["children"][0]["kind"] == "primitive"
            and inner2["children"][0]["value"] == "1"
        )
        assert (
            inner2["children"][1]["kind"] == "primitive"
            and inner2["children"][1]["value"] == "2"
        )
