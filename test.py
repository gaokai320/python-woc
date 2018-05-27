
import requests
import unittest

from oscar import *


class TestRelations(unittest.TestCase):
    """
    List of all relations and data file locations
    https://bitbucket.org/swsc/lookup/src/master/README.md
    author2commit - done
    author2file
    blob2commit - done // 4x  Fails
    commit2blob
    commit2project - done
    file2commit - done  // Fails
    project2commit - done
    """

    def test_author_commit(self):
        proj = 'user2589_minicms'
        authors = ('Marat <valiev.m@gmail.com>',
                   'user2589 <valiev.m@gmail.com>')
        commits = {c.sha: c for c in Project(proj).commits}

        for author in authors:
            relation = {c.sha: c for c in Author(author).commits}
            for sha, c in relation.items():
                self.assertEqual(
                    c.author, author,
                    "Author2Cmt lists commit %s as authored by %s, but it is "
                    "%s" % (sha, author, c.author))

            relation = {sha for sha in relation if sha in commits}
            cs = {sha for sha, c in commits.items() if c.author == author}
            diff = relation - cs
            self.assertFalse(
                diff, "Author2Cmt lists commits %s as authored by %s, but"
                      "they are not" % (",".join(diff), author))
            diff = cs - relation
            self.assertFalse(
                diff, "Author2Cmt does not list commits %s as authored by %s,"
                      "but they are" % (",".join(diff), author))

    def test_blob_commits_delete(self):
        """ Test blob2Cmt
        Test if a commit is contained in relations of all blobs it deleted
        """
        # this commit deletes MANIFEST.in
        # https://github.com/user2589/minicms/commit/SHA
        # Blob('7e2a34e2ec9bfdccfa01fff7762592d9458866eb')
        commit_sha = '2881cf0080f947beadbb7c240707de1b40af2747'
        commit = Commit(commit_sha)
        parent = commit.parents.next()

        # files that are in parent but not in commit
        # These are not present in blob.commits by some reason
        blobs = {parent.tree.files[fname] for fname in
                 set(parent.tree.files.keys()) - set(commit.tree.files.keys())}

        for sha in blobs:
            self.assertIn(
                commit_sha, Blob(sha).commit_shas,
                "Blob2Cmt doesn't list commit %s for blob %s,"
                "but it but it was deleted in this commit" % (commit_sha, sha))

    def test_blob_commits_change(self):
        """ Test blob2Cmt
        Test if a commit is contained in relations of all blobs it changed
        """
        # this commit changes a bunch of files
        # https://github.com/user2589/minicms/commit/SHA
        commit_sha = 'ba3659e841cb145050f4a36edb760be41e639d68'
        commit = Commit(commit_sha)
        parent = commit.parents.next()

        blobs = {sha for fname, sha in commit.tree.files.items()
                 if parent.tree.files.get(fname) != sha}

        for sha in blobs:
            self.assertIn(
                commit_sha, Blob(sha).commit_shas,
                "Blob2Cmt doesn't list commit %s for blob %s,"
                "but it but it was changed in this commit" % (commit_sha, sha))

    def test_blob_commits_add(self):
        """ Test blob2Cmt
        Test if a commit is contained in relations of all blobs it added
        """
        # this is the first commit in user2589_minicms
        # https://github.com/user2589/minicms/commit/SHA
        commit_sha = '1e971a073f40d74a1e72e07c682e1cba0bae159b'
        commit = Commit(commit_sha)

        blobs = set(commit.tree.files.values())

        for sha in blobs:
            self.assertIn(
                commit_sha, Blob(sha).commit_shas,
                "Blob2Cmt doesn't list commit %s for blob %s,"
                "but it but it was added in this commit" % (commit_sha, sha))

    def test_blob_commits_all(self):
        """ Test blob2Cmt
        Test if all commit where a blob was modified are contained
        in the relation
        """
        # the first version of Readme.rst in user2589_minicms
        # it was there for only one commit, so:
        #     introduced in 2881cf0080f947beadbb7c240707de1b40af2747
        #     removed in 85787429380cb20b6a935e52c50f85f455790617
        # Feel free to change to any other blob from that project
        proj = 'user2589_minicms'
        blob_sha = 'c3bfa5467227e7188626e001652b85db57950a36'
        commits = {c.sha: c for c in Project(proj).commits}
        present = {sha: blob_sha in c.tree.files.values()
                   for sha, c in commits.items()}

        # commit is changing a blob if:
        #   all of parents have it and this commit doesn't
        #   neither of parents have it and commit does
        changed = {c.sha for sha, c in commits.items()
                   if ((c.parent_shas
                        and all(present[p] for p in c.parent_shas)
                        and not present[c.sha])
                       or (not any(present[p] for p in c.parent_shas)
                           and present[c.sha])
                       )}

        # just in case this blob is not unique to the project,
        # e.g. a license file, filter first
        relation = {sha for sha in Blob(blob_sha).commit_shas
                    }.intersection(commits.keys())

        diff = relation - changed
        self.assertFalse(
            diff, "Blob2Cmt indicates blob %s was changed in "
                  "commits %s, but it was not" % (blob_sha, ",".join(diff)))

        diff = changed - relation
        self.assertFalse(
            diff, "Blob2Cmt indicates blob %s was NOT changed in "
                  "commits %s, but it was" % (blob_sha, ",".join(diff)))

    def test_commit_projects(self):
        for proj in ('user2589_minicms', 'user2589_karta'):
            for c in Project(proj).commits:
                self.assertIn(
                    proj, c.project_names,
                    "Cmt2PrjG asserts commit %s doesn't belong to project %s, "
                    "but it does" % (c.sha, proj))

    def test_file_commits(self):
        proj = 'user2589_minicms'
        fname = 'minicms/templatetags/minicms_tags.py'
        commits = {c.sha: c for c in Project(proj).commits}

        changed = set()
        for sha, c in commits.items():
            ptrees = [p.tree.files for p in c.parents] or [{}]
            if all(pt.get(fname) != c.tree.files.get(fname) for pt in ptrees):
                changed.add(sha)

        # only consider changes in this project
        relation = {sha for sha in File(fname).commit_shas if sha in commits}

        diff = relation - changed
        self.assertFalse(
            diff, "File2Cmt indicates file %s was changed in "
                  "commits %s, but it was not" % (fname, ",".join(diff)))

        diff = changed - relation
        self.assertFalse(
            diff, "File2Cmt indicates file %s was NOT changed in "
                  "commits %s, but it was" % (fname, ",".join(diff)))

    def test_project_commits(self):
        # select something long abandoned and with <100 commits
        project = 'user2589_minicms'
        relation = {c.sha for c in Project(project).commits}
        url = "https://api.github.com/repos/%s/commits?" \
              "per_page=100" % project.replace("_", "/")
        github = {c['sha'] for c in requests.get(url).json()}

        diff = relation - github
        self.assertFalse(
            diff, "Prj2Cmt lists commits %s in project %s but they're not on "
                  "github" % (",".join(diff), project))

        diff = github - relation
        self.assertFalse(
            diff, "Prj2Cmt doesn't list commits %s in project %s but they're "
                  "on github" % (",".join(diff), project))