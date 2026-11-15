# Barcha modellarni import qilish (jadvallar avtomatik yaratilishi uchun)
from models.user import User, Student, Teacher, Subscription, OTPCode, ParentContact  # noqa: F401
from models.group import Group, GroupMember  # noqa: F401
from models.grid import GridColumn, GridCell  # noqa: F401
from models.attendance import Attendance, TeacherSettings  # noqa: F401
from models.lesson import Lesson, LessonSlide  # noqa: F401
from models.assignment import Assignment, Submission  # noqa: F401
from models.test import Test, Question, TestAttempt, RetakeRequest  # noqa: F401
from models.ai_chat import ChatSession, ChatMessage  # noqa: F401
from models.message import DirectMessage, ParentMessage  # noqa: F401
from models.ticket import Ticket  # noqa: F401
from models.payment import Payment  # noqa: F401
from models.telegram import TelegramAccount, ParentLink  # noqa: F401
from models.automation import StudentPenalty, DangerZoneState, ParentAlert  # noqa: F401
from models.book import Book, VocabUnit, VocabAttempt, VocabRetake, VocabFinalAttempt  # noqa: F401
