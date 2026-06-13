from django.test import TestCase
from django.contrib.auth import get_user_model
from app.models import Source, Researcher, Project, Observation

User = get_user_model()

class UserDeletionTestCase(TestCase):
    fixtures = [
        "units.json",
    ]

    def setUp(self):
        # Create users/researchers
        self.user1 = User.objects.create_user(username="user1", email="user1@soton.ac.uk", password="password")
        self.researcher1 = Researcher.objects.create(user=self.user1, affiliations="Affil 1", orcid="0000-0000-0000-0001")
        
        self.user2 = User.objects.create_user(username="user2", email="user2@soton.ac.uk", password="password")
        self.researcher2 = Researcher.objects.create(user=self.user2, affiliations="Affil 2", orcid="0000-0000-0000-0002")

        # Create a source
        self.source = Source.objects.create(
            name="Test Source",
            ra=10.0,
            dec=-10.0,
            is_valid=True,
            created_by=self.researcher1
        )

    def test_delete_user_sole_project_owner(self):
        # Create a project where researcher1 is the sole owner (PI and no members)
        project = Project.objects.create(
            name="Sole Project",
            description="A project with only one researcher",
            principal_investigator=self.researcher1,
            is_valid=True
        )

        # Create an observation by researcher1 in this project
        obs = Observation.objects.create(
            source=self.source,
            project=project,
            observer=self.researcher1,
            is_valid=True,
            jd=2450000.0
        )

        # Delete user1
        self.user1.delete()

        # Project and observation should be deleted
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())
        self.assertFalse(Observation.objects.filter(pk=obs.pk).exists())
        # Source should NOT be deleted (since on_delete=SET_NULL now)
        self.assertTrue(Source.objects.filter(pk=self.source.pk).exists())
        self.assertNil = Source.objects.get(pk=self.source.pk).created_by
        self.assertIsNone(self.assertNil)

    def test_delete_member_keeps_project(self):
        # Create a project where researcher1 is PI and researcher2 is member
        project = Project.objects.create(
            name="Shared Project",
            description="A project with multiple researchers",
            principal_investigator=self.researcher1,
            is_valid=True
        )
        project.members.add(self.researcher2)

        # Create observation by researcher2 (the member)
        obs = Observation.objects.create(
            source=self.source,
            project=project,
            observer=self.researcher2,
            is_valid=True,
            jd=2450000.0
        )

        # Delete user2 (the member)
        self.user2.delete()

        # Project should NOT be deleted
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())
        # Observation by user2 in a kept project should NOT be deleted
        self.assertTrue(Observation.objects.filter(pk=obs.pk).exists())
        
        project.refresh_from_db()
        self.assertEqual(project.principal_investigator, self.researcher1)
        self.assertNotIn(self.researcher2, project.members.all())

    def test_delete_pi_keeps_project_and_promotes_member(self):
        # Create a project where researcher1 is PI and researcher2 is member
        project = Project.objects.create(
            name="Shared Project 2",
            description="A project where PI will be deleted",
            principal_investigator=self.researcher1,
            is_valid=True
        )
        project.members.add(self.researcher2)

        # Delete user1 (the PI)
        self.user1.delete()

        # Project should NOT be deleted
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())
        
        # researcher2 should be promoted to PI
        project.refresh_from_db()
        self.assertEqual(project.principal_investigator, self.researcher2)
        # researcher1 should be removed from members (if they were in there)
        self.assertNotIn(self.researcher1, project.members.all())
