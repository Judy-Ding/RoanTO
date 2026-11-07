from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]

MISSIONS = [
    {
        "id": "ttc-first-trip",
        "title": "My First TTC Trip",
        "category": "Navigate",
        "description": "Understand the basics and plan a confident first ride.",
        "preference_fields": [
            {"id": "starting_location", "label": "Where will you start?", "placeholder": "Neighbourhood or nearest intersection"},
            {"id": "destination", "label": "Where would you like to go?", "placeholder": "Destination or neighbourhood"},
            {"id": "available_time", "label": "When are you planning to travel?", "placeholder": "e.g. weekday morning, this weekend"},
            {"id": "transportation", "label": "Any travel preferences?", "placeholder": "e.g. fewer transfers, step-free route"},
        ],
    },
    {
        "id": "plan-ttc-commute",
        "title": "Plan a TTC Commute",
        "category": "Navigate",
        "description": "Get familiar with planning a regular trip across the city.",
        "preference_fields": [
            {"id": "starting_location", "label": "Where will you start?", "placeholder": "Neighbourhood or nearest intersection"},
            {"id": "destination", "label": "Where do you commute to?", "placeholder": "Destination or neighbourhood"},
            {"id": "available_time", "label": "When do you usually travel?", "placeholder": "e.g. weekday mornings"},
            {"id": "transportation", "label": "Any travel preferences?", "placeholder": "e.g. fewer transfers, step-free route"},
        ],
    },
    {
        "id": "presto-basics",
        "title": "Learn PRESTO Basics",
        "category": "Navigate",
        "description": "Understand how to get started with fare payment.",
        "preference_fields": [
            {"id": "current_fare_setup", "label": "What do you use to pay today?", "placeholder": "e.g. single tickets, PRESTO card, not sure"},
            {"id": "learning_focus", "label": "What would you like to understand?", "placeholder": "e.g. how to load a card or compare payment options"},
        ],
    },
    {
        "id": "library-start",
        "title": "Get Started with Toronto Public Library",
        "category": "Settle",
        "description": "Learn how to explore library services and get a card.",
        "preference_fields": [
            {"id": "neighbourhood", "label": "Which area is convenient for you?", "placeholder": "Neighbourhood or nearby intersection"},
            {"id": "library_use", "label": "What would you like to use the library for?", "placeholder": "e.g. books, study space, events, internet"},
        ],
    },
    {
        "id": "find-health-care",
        "title": "Find a Family Doctor",
        "category": "Settle",
        "description": "Explore practical ways to look for ongoing primary care.",
        "preference_fields": [
            {"id": "neighbourhood", "label": "Which area are you looking in?", "placeholder": "Neighbourhood or city area"},
            {"id": "care_search_stage", "label": "Where are you in your search?", "placeholder": "e.g. just getting started, already on a waitlist"},
        ],
    },
    {
        "id": "newcomer-services",
        "title": "Explore Newcomer Services",
        "category": "Settle",
        "description": "Find local support and services for settling in Toronto.",
        "preference_fields": [
            {"id": "neighbourhood", "label": "Which area are you in?", "placeholder": "Neighbourhood or city area"},
            {"id": "service_type", "label": "What kind of support are you looking for?", "placeholder": "e.g. language classes, employment, housing"},
        ],
    },
    {
        "id": "toronto-on-a-budget",
        "title": "Discover Toronto on a Budget",
        "category": "Explore",
        "description": "Find approachable, low-cost ways to experience the city.",
        "preference_fields": [
            {"id": "starting_location", "label": "Where would you like to start?", "placeholder": "Neighbourhood or city area"},
            {"id": "budget", "label": "What budget works for you?", "placeholder": "e.g. free, up to $20"},
            {"id": "available_time", "label": "How much time do you have?", "placeholder": "e.g. a couple of hours, a full day"},
            {"id": "transportation", "label": "How would you like to get around?", "placeholder": "e.g. walking, TTC, cycling"},
        ],
    },
    {
        "id": "explore-neighbourhood",
        "title": "Explore a Toronto Neighbourhood",
        "category": "Explore",
        "description": "Plan a relaxed first visit to a neighbourhood.",
        "preference_fields": [
            {"id": "neighbourhood", "label": "Which neighbourhood interests you?", "placeholder": "Name an area, or say you are open to ideas"},
            {"id": "interests", "label": "What would you enjoy doing?", "placeholder": "e.g. parks, food, arts, local history"},
            {"id": "available_time", "label": "How much time do you have?", "placeholder": "e.g. a couple of hours, an afternoon"},
            {"id": "transportation", "label": "How would you like to get around?", "placeholder": "e.g. walking, TTC, cycling"},
        ],
    },
    {
        "id": "free-city-activities",
        "title": "Find Free Things to Do",
        "category": "Explore",
        "description": "Look for no-cost activities and public spaces around the city.",
        "preference_fields": [
            {"id": "neighbourhood", "label": "Which area should we focus on?", "placeholder": "Neighbourhood or open to anywhere"},
            {"id": "interests", "label": "What kinds of activities interest you?", "placeholder": "e.g. parks, museums, community events"},
            {"id": "available_time", "label": "When do you have time?", "placeholder": "e.g. weekday evening, Saturday"},
            {"id": "transportation", "label": "How would you like to get around?", "placeholder": "e.g. walking, TTC, cycling"},
        ],
    },
    {
        "id": "community-activity",
        "title": "Find a Community Activity",
        "category": "Connect",
        "description": "Choose a welcoming activity and figure out how to join.",
        "preference_fields": [
            {"id": "neighbourhood", "label": "Which area is convenient?", "placeholder": "Neighbourhood or city area"},
            {"id": "interests", "label": "What activities do you enjoy?", "placeholder": "e.g. sports, arts, games, language exchange"},
            {"id": "availability", "label": "When are you generally available?", "placeholder": "e.g. weekday evenings, weekends"},
        ],
    },
    {
        "id": "volunteer-toronto",
        "title": "Find a Volunteer Opportunity",
        "category": "Connect",
        "description": "Explore ways to contribute and meet people locally.",
        "preference_fields": [
            {"id": "neighbourhood", "label": "Which area can you get to?", "placeholder": "Neighbourhood or city area"},
            {"id": "interests", "label": "What causes or activities interest you?", "placeholder": "e.g. environment, food programs, events"},
            {"id": "availability", "label": "When are you generally available?", "placeholder": "e.g. weekday evenings, weekends"},
        ],
    },
    {
        "id": "meet-neighbours",
        "title": "Meet People in Your Community",
        "category": "Connect",
        "description": "Find welcoming ways to connect with people nearby.",
        "preference_fields": [
            {"id": "neighbourhood", "label": "Which area would you like to connect in?", "placeholder": "Neighbourhood or city area"},
            {"id": "interests", "label": "What do you enjoy doing with others?", "placeholder": "e.g. sports, crafts, conversation, volunteering"},
            {"id": "availability", "label": "When are you generally available?", "placeholder": "e.g. weekday evenings, weekends"},
        ],
    },
]

MISSION_BY_ID = {mission["id"]: mission for mission in MISSIONS}


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Preferences(APIModel):
    starting_location: str = Field(default="", max_length=200)
    destination: str = Field(default="", max_length=200)
    available_time: str = Field(default="", max_length=100)
    budget: str = Field(default="", max_length=100)
    transportation: str = Field(default="", max_length=100)
    current_fare_setup: str = Field(default="", max_length=200)
    learning_focus: str = Field(default="", max_length=300)
    neighbourhood: str = Field(default="", max_length=200)
    library_use: str = Field(default="", max_length=300)
    care_search_stage: str = Field(default="", max_length=200)
    service_type: str = Field(default="", max_length=200)
    interests: str = Field(default="", max_length=300)
    availability: str = Field(default="", max_length=100)
    additional_instructions: str = Field(default="", max_length=1000)


class ActionStep(APIModel):
    title: ShortText
    details: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class OfficialResource(APIModel):
    title: ShortText
    url: HttpUrl


class PlanContent(APIModel):
    goal: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
    overview: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=1200)]
    steps: list[ActionStep] = Field(min_length=3, max_length=5)
    practical_tips: list[ShortText] = Field(min_length=1, max_length=8)
    resources: list[OfficialResource] = Field(default_factory=list, max_length=5)
    verify_before_you_go: list[ShortText] = Field(min_length=1, max_length=8)


class PlanDraft(APIModel):
    mission_id: str
    custom_goal: str | None = Field(default=None, min_length=5, max_length=200)
    preferences: Preferences
    content: PlanContent


class GenerateRequest(APIModel):
    mission_id: str
    custom_goal: str | None = Field(default=None, min_length=5, max_length=200)
    preferences: Preferences = Field(default_factory=Preferences)


class ModifyRequest(APIModel):
    plan: PlanDraft
    request: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class StepCompletion(APIModel):
    completed: bool


class MissionCompletion(APIModel):
    completed: bool


class SavedStep(ActionStep):
    completed: bool = False


class SavedPlanContent(APIModel):
    goal: str
    overview: str
    steps: list[SavedStep]
    practical_tips: list[str]
    resources: list[OfficialResource]
    verify_before_you_go: list[str]


class PlanRecord(APIModel):
    id: str
    user_id: str
    mission_id: str
    mission_title: str
    category: str
    preferences: Preferences
    content: SavedPlanContent
    mission_completed: bool
    created_at: str
    updated_at: str
