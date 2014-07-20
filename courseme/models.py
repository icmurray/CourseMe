from courseme import db
import json, operator
from datetime import datetime, timedelta
import md5
from sqlalchemy import desc

ROLE_USER = 0
ROLE_ADMIN = 1

VIEW_ALL = 0
VIEW_SYSTEM = 1
VIEW_OWN = 2


ENTERPRISE_LICENCE_DURATION = 1

student_tutor = db.Table("student_tutor",
    db.Column("tutor_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("student_id", db.Integer, db.ForeignKey("user.id"))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    password = db.Column(db.String(120), index = True, nullable=False)      #DJG - What does index=True do?
    email = db.Column(db.String(120), index = True, unique = True, nullable=False)
    name = db.Column(db.String(64), index = True, nullable=False)
    blurb = db.Column(db.String(240), default = "This is some blurb")
    role = db.Column(db.SmallInteger, default = ROLE_USER, nullable=False)
    last_seen =  db.Column(db.DateTime)
    time_registered = db.Column(db.DateTime)
    enterprise_licence = db.Column(db.DateTime)
    view_system_only = db.Column(db.Boolean, default = False)  
    time_deleted = db.Column(db.DateTime)
    
    view_institution_only_id = db.Column(db.Integer, db.ForeignKey('institution.id'))           
    institution_student_id = db.Column(db.Integer, db.ForeignKey('institution.id'))
    
    view_institution_only = db.relationship("Institution", primaryjoin="Institution.id==User.view_institution_only_id", backref="users_viewing_approved")
    objectives_created = db.relationship("Objective", backref="created_by", lazy='dynamic')
    modules_authored = db.relationship("Module", backref="author", lazy = 'dynamic')
    institutions_created = db.relationship("Institution", primaryjoin="Institution.creator_id==User.id", backref="creator", lazy='dynamic')
    groups_created = db.relationship("Group", primaryjoin="Group.creator_id==User.id", backref="creator", lazy='dynamic')

    students = db.relationship("User",
                    secondary=student_tutor,
                    primaryjoin=(student_tutor.c.tutor_id==id),
                    secondaryjoin=(student_tutor.c.student_id==id),
                    backref = db.backref('tutors', lazy = 'dynamic'),           #DJG - Does this need to be included to make the secondary table update when an objective is passed to session.delete()? 
                    lazy = 'dynamic',                                           #DJG - not the default, don't know why I need it: the attribute will return a pre-configured Query object for all read operations, onto which further filtering operations can be applied before iterating the results.
                    passive_updates=False)  

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % (self.name)
    
    def avatar(self, size=50):
        return 'http://www.gravatar.com/avatar/' + md5(self.email).hexdigest() + '?d=mm&s=' + str(size)

    def is_enterprise_licenced(self):
        if self:
            if self.role == ROLE_ADMIN:
                return True
            if self.enterprise_licence:
                licence_expiry_date = self.enterprise_licence + timedelta(years = ENTERPRISE_LICENCE_DURATION)
                if datetime.utcnow() <= licence_expiry_date :
                    return True
                else:
                    Message.AdminMessage(
                        to_id = self.id,
                        subject = "Enterprise Licence Expired",
                        body = "You have tried to perform an action requiring an enterprise licence. Your licence expired on " + licence_expiry_date + ". To renew your licence contact CourseMe at " + User.main_admin_user().email
                    )
                    return False
            else:
                Message.AdminMessage(
                    to_id = self.id,
                    subject = "Enterprise Licence Needed",
                    body = "You have tried to perform an action requiring an enterprise licence. To purchase a licence contact CourseMe at " + User.main_admin_user().email
                    )
                return False                

    def visible_objectives(self):
        visible_objective_user_ids = [u.id for u in User.admin_users()]
        visible_objective_user_ids.append(self.id)
        return Objective.query.filter(Objective.created_by_id.in_(visible_objective_user_ids))      #DJG - what about visible courses?

    def live_modules_authored(self):
        return Module.LiveModules().filter_by(author_id = self.id)

    def live_modules_authored_by_type(self, type):
        return self.live_modules_authored().filter_by(material_type = type)

    def live_modules_viewed(self):
        #return Module.LiveModules().filter(Module.id.in_(UserModule.query.filter_by(user=self).all()))
        return Module.LiveModules().join(UserModule).filter(UserModule.user == self)    

    def visible_modules(self):
        #import pdb; pdb.set_trace()            #DJG - remove
        query_authored_modules = self.live_modules_authored()
        query_viewed_modules = self.live_modules_viewed()
        institution_student = self.institution_student
        query_student_modules = Module.LiveModules()
        if institution_student:
            if institution_student.view_institution_only:
                query_student_modules = institution_student.view_institution_only.approved_modules
        if self.view_institution_only:
            query_select_modules = self.view_institution_only.approved_modules
        else:
            query_select_modules = Module.LiveModules()
        query_approved_modules = query_select_modules.intersect(query_student_modules)
        
        return query_approved_modules.union(query_authored_modules, query_viewed_modules)
        
    def enrolled_courses(self):
        #return [Module.query.get(um.module_id) for um in UserModule.query.filter_by(user=self).filter(UserModule.enrolled).order_by(desc(UserModule.last_viewed)).all()]        #DJG - can we do better with filter on boolean type?
        return self.live_modules_viewed().filter(UserModule.enrolled).filter(Module.material_type=='Course').order_by(desc(UserModule.last_viewed))
    
    def recent_modules(self, count):
        #import pdb; pdb.set_trace()        #DJG - remove
        #return self.live_modules_viewed().order_by(desc(UserModule.last_viewed)).limit(count).all()     #DJG - working but not on index page
        return []
    
    def relevant_institutions(self):
        #DJG - must be able to do better than this!
        relevant_institutions = [Institution.main_courseme_institution()]
        relevant_institutions.extend(self.institutions_created.all())
        relevant_institutions.extend(self.institutions_member.all())
        if self.institution_student: relevant_institutions.append(self.institution_student)
        relevant_institutions = list(set(relevant_institutions))
        print relevant_institutions         #DJG - remove this
        return relevant_institutions
        
    @staticmethod
    def make_unique_username(username):
        if User.query.filter_by(name = username).first() == None:
            return username
        version = 2
        while True:
            new_username = username + str(version)
            if User.query.filter_by(name = new_username).first() == None:
                break
            version += 1
        return new_username

    @staticmethod       #DJG - suspect this should be taken out of the user class as the user is passed to the template and so the server side through g.user - may therefore give access to the client about admin users?
    def admin_users():
        return User.query.filter(User.role == ROLE_ADMIN).all()

    @staticmethod 
    def main_admin_user():
        return User.query.get(1)
        #DJG - Not robust. Need some way to return the main system admin user


objective_heirarchy = db.Table("objective_heirarchy",
    db.Column("prerequisite_id", db.Integer, db.ForeignKey("objective.id")),
    db.Column("followon_id", db.Integer, db.ForeignKey("objective.id"))
)

class Objective(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))     #DJG - why is user lower case in ForeignKey('user.id')    

    prerequisites = db.relationship("Objective",
                        secondary=objective_heirarchy,
                        primaryjoin=(objective_heirarchy.c.followon_id==id),
                        secondaryjoin=(objective_heirarchy.c.prerequisite_id==id),
                        backref = db.backref('followons', lazy = 'dynamic'),        #DJG - Does this need to be included to make the secondary table update when an objective is passed to session.delete()? 
                        lazy = 'dynamic',                                           #DJG - not the default, don't know why I need it: the attribute will return a pre-configured Query object for all read operations, onto which further filtering operations can be applied before iterating the results.
                        passive_updates=False)                                      #DJG - Does this need to be included to make the secondary table update when an objective is passed to session.delete()? 
    
    def require(self, objective):
        if not self.is_required(objective):
            self.prerequisites.append(objective)
            return self

    def unrequire(self, objective):
        if self.is_required(objective):
            self.prerequisites.remove(objective)
            return self

    def is_required_direct(self, objective):
        return self == objective or self.prerequisites.filter(objective_heirarchy.c.prerequisite_id == objective.id).count() > 0

    def is_required_indirect(self, objective):
        return self == objective or objective in self.all_prerequisites()

    def score(self):
        prerequisites = self.prerequisites.all()
        if prerequisites:
            return max(p.score() for p in prerequisites)+1
        else:
            return 1
    
    def all_prerequisites(self):
        all_prerequisites = set()
        prerequisites_found = set(self.prerequisites.all())
        while prerequisites_found:
            all_prerequisites = set.union(all_prerequisites, prerequisites_found)
            prerequisites_found_iterator = (set(p.prerequisites) for p in prerequisites_found)
            prerequisites_found = set.union(*prerequisites_found_iterator)          #DJG - http://stackoverflow.com/questions/14720436/set-union-complains-that-it-has-no-argument-when-passing-in-a-generator
        return list(all_prerequisites)
   
    def as_dict(self):
        #wouldn't handle relationships
        #public_fields = ['name']
        #return {key: getattr(self, key) for key in public_fields}  
        
        data = {}
        data['id'] = self.id
        data['name'] = self.name
        data['prerequisites'] = [p.name for p in self.prerequisites.all()]
        #return json.dumps(data, sort_keys=True, separators=(',',':'))      DJG - could convert to JSON in here
        return data

    def top_modules(self, exclude=None, material_type="Lecture", num=3):
        modules = self.modules.filter_by(material_type=material_type).order_by(Module.votes).limit(num+1).all()  #DJG - lookup modules for given objective sorted by votes of given type
        if exclude and exclude in modules: modules.remove(exclude)
        return modules[:num]

    @staticmethod
    def system_objectives():
        system_objectives_iterator = (set(u.objectives_created) for u in User.admin_users())
        system_objectives = set.union(*system_objectives_iterator)
        return system_objectives
    
module_objectives = db.Table('module_objectives',
    db.Column('module_id', db.Integer, db.ForeignKey('module.id')),
    db.Column('objective_id', db.Integer, db.ForeignKey('objective.id'))
)

course_modules = db.Table('course_modules',
    db.Column('course_id', db.Integer, db.ForeignKey('module.id')),
    db.Column('module_id', db.Integer, db.ForeignKey('module.id'))
)
    
class Module(db.Model):                                             #DJG - change this class to material as it now captures modules and courses
    id = db.Column(db.Integer, primary_key = True)      
    name = db.Column(db.String(120))
    description = db.Column(db.String(400))
    notes = db.Column(db.String(400))
    material_type = db.Column(db.String(120), default = 'Lecture')
    time_created = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime)
    material_source = db.Column(db.String(120), default = 'youtube')
    material_path = db.Column(db.String(400))
    submitted = db.Column(db.DateTime) 
    published = db.Column(db.DateTime)
    locked = db.Column(db.DateTime)
    deleted = db.Column(db.DateTime)
    live = db.Column(db.Boolean, default = True)
    subtitles = db.Column(db.Boolean, default = False)
    easy_language = db.Column(db.Boolean, default = False)
    extension = db.Column(db.Boolean, default = False)
    for_teachers = db.Column(db.Boolean, default = False)

    votes = db.Column(db.Integer, default = 0)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))     #DJG - why is user lower case in ForeignKey('user.id')

    objectives = db.relationship('Objective', secondary=module_objectives,
        backref=db.backref('modules', lazy='dynamic'))

    modules = db.relationship("Module",
                        secondary=course_modules,
                        primaryjoin=(course_modules.c.course_id==id),
                        secondaryjoin=(course_modules.c.module_id==id),
                        backref = db.backref('courses', lazy = 'dynamic'),        #DJG - Does this need to be included to make the secondary table update when an objective is passed to session.delete()? 
                        lazy = 'dynamic',                                       
                        passive_updates=False)

    def calculate_votes():
        pass #DJG - calculate the proper votes total by summing usermodules and store in this parameter, to be run periodically to keep votes count properly alligned; should print out a record if mismatched to developer log

    def icon_class(self):
        icon_classes = {"Course": "glyphicon glyphicon-list-alt",
                        "Lecture": "glyphicon glyphicon-play-circle",
                        "Exercise": "glyphicon glyphicon-check",
                        "Tool": "glyphicon glyphicon-wrench"
                        }
        return icon_classes[self.material_type]

    def is_courseable(self):
        return self.material_type != "Course"

    def delete(self, alternative=0):
        self.deleted = datetime.utcnow()
        self.live = False
        for course in self.courses.all():
            course.modules.remove(self)
        for um in self.user_modules:
            um.delete(alternative)
        db.session.commit()

    def course_objectives(self):
        if self.material_type == "Course":
            course_objectives = [obj for mod in self.modules for obj in mod.objectives]
            course_objectives = list(set(course_objectives))
            course_objectives.sort(key=operator.methodcaller("score"))
            return course_objectives
        else:
            return self.objectives

    def as_dict(self):
        result = self.__dict__
        result['author'] = self.author.name
        result['objectives'] = [o.name for o in self.objectives]
        del result['_sa_instance_state']
        return result

    def add_to_author_institutions(self):
        for i in self.author.institutions:
            i.approved_modules = i.approved_modules.append(self)
        

    @staticmethod
    def LiveModules():
        return Module.query.filter(Module.live)
    
class UserModule(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    module_id = db.Column(db.Integer, db.ForeignKey(Module.id))
    first_viewed = db.Column(db.DateTime)
    last_viewed = db.Column(db.DateTime)
    starred = db.Column(db.Boolean, default = False)
    vote = db.Column(db.Integer, default = 0)
    notes = db.Column(db.String(1000))
    enrolled = db.Column(db.Boolean, default = False)
    deleted = db.Column(db.Boolean, default = False)

    user = db.relationship(User, backref='user_modules')
    module = db.relationship(Module, backref='user_modules')
    
    
    def part_of_course(self, relevance="enrolled"):
        courses = []
        if relevance == "enrolled":
            courses = self.user.enrolled_courses().all()
        elif relevance == "authored":
            courses = self.user.modules_authored.all()
        for course in courses:
            if course.material_type=="Course":
                if self.module in course.modules:
                    return course
        return None

    def completed(self):
        #import pdb; pdb.set_trace()
        if self:
            if self.module.material_type != "Course":
                return 1                #DJG - need some better logic here about whether a lecture or exercise has been completed
            else:
                course_module_ids = [mod.id for mod in self.module.modules]
                course_length = len(course_module_ids)
                return sum(um.completed() for um in UserModule.query.filter_by(user_id=self.user.id).filter(UserModule.module_id.in_(course_module_ids)).all())/course_length
        else:
            return 0

    def course_completed(self):
        course = self.part_of_course()
        if course:    
            user_course = UserModule.query.filter_by(user_id=self.user.id, module_id=course.id).first()
            return user_course.completed()
        else:
            return 0 

    def important(self, recent=7):
        message = ""
        material_type = self.module.material_type
        authored_course = self.part_of_course("authored")
        if authored_course: return material_type + " you are using in your Course '" + authored_course.name + "'"
        if self.enrolled: return material_type + " you have enrolled in"
        if self.part_of_course(): return material_type + " within a Course you have enrolled in"
        if self.starred: return "Starred " + material_type  
        if self.last_viewed >= datetime.now()-timedelta(days = recent): return "recently viewed " + material_type

    
    def delete(self, alternative=0):
        self.deleted = True
        important = self.important()
        if important:
            body="A " + important + ", " + self.module.name + ", has been deleted."
            if alternative: pass
            Message.AdminMessage(to_id=self.user.id,
                                 subject="Material Deleted",
                                 body=body,
                                 recommended_material_id=alternative)
        db.session.commit()
    
    def as_json(self):
        data = {}
        data['id'] = self.id
        data['starred'] = self.starred
        data['vote'] = self.vote
        return json.dumps(data, sort_keys=True, separators=(',',':'))
    

    @staticmethod
    def FindOrCreate(user_id, module_id):
        usermodule = UserModule.query.filter_by(user_id=user_id, module_id=module_id).first()
        if usermodule is None:
            usermodule = UserModule(user_id=user_id,
                                    module_id=module_id,
                                    first_viewed=datetime.utcnow())
            #print "usermodule " + str(usermodule.id) + " created"       #DJG - delete
        else:
            pass    #print "usermodule " + str(usermodule.id) + " found"         #DJG - delete
        usermodule.last_viewed=datetime.utcnow()
        db.session.add(usermodule)
        db.session.commit()
        return usermodule


class Message(db.Model):     #DJG - probably need a separate one for module and course recommendations, need to add the relationship to the material being recommended and all the permissions
    id = db.Column(db.Integer, primary_key = True)
    from_id = db.Column(db.Integer, db.ForeignKey(User.id))
    to_id = db.Column(db.Integer, db.ForeignKey(User.id))
    subject = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=True)
    sent = db.Column(db.DateTime)
    read = db.Column(db.DateTime)
    recommended_material_id = db.Column(db.Integer, db.ForeignKey(Module.id))
    request_access = db.Column(db.Boolean, default = False)

    from_user = db.relationship(User, foreign_keys=[from_id], backref='sent_messages')
    to_user = db.relationship(User, foreign_keys=[to_id], backref='received_messages')
    recommended_material = db.relationship(Module, foreign_keys=[recommended_material_id], backref='recommendations')
    
    @staticmethod
    def AdminMessage(to_id, subject, body="", recommended_material_id=0):
        admin_message = Message(from_id=User.main_admin_user().id,
                to_id=to_id,
                subject=subject,
                body=body,
                sent=datetime.utcnow(),
                recommended_material_id=recommended_material_id)
        db.session.add(admin_message)
        db.session.commit()



group_members = db.Table('group_members',
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
    db.Column('member_id', db.Integer, db.ForeignKey('user.id'))
)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(120))    
    creator_id = db.Column(db.Integer, db.ForeignKey(User.id, use_alter=True, name='fk_group_creator_id'), nullable=False)        #DJG - need , use_alter=True, name='fk_institution_creator_id' to avoid circular join references

    members = db.relationship(User, secondary=group_members, lazy='dynamic',
        backref=db.backref('groups_member', lazy='dynamic'))
    
    def is_member(self, user):
        return self.members.filter(group_members.c.member_id == user.id).count() > 0

    def add_member(self, user):
        if user:
            if not self.is_member(user):
                self.members.append(user)
                #DJG - May not need to inform users if they are added to a group - purely an organisational tool for people to send messages and track proress
                #message = Message(
                #    from_id = self.creator_id,
                #    to_id = user.id,
                #    subject = "You have been added to the group " + self.name,
                #    body = "You have been added to the group " + self.name + ". If you want to leave this group go to the groups section of your profile page and click the button to leave.",
                #    sent = datetime.utcnow())
                #db.session.add(message)            
                db.session.add(self)
                db.session.commit()
        else:
            pass

    def message(self, subject, recommended_material_id):
        for memeber in self.members:
            message = Message(
                from_id = self.creator_id,
                to_id = member.id,
                subject = subject,            
                body = body,
                sent=datetime.utcnow(),
                recommended_material_id=recommended_material_id
                )
            db.session.add(message)
            db.session.commit()


institution_members = db.Table('institution_members',
    db.Column('institution_id', db.Integer, db.ForeignKey('institution.id')),
    db.Column('member_id', db.Integer, db.ForeignKey('user.id'))
)

institution_approved_modules = db.Table('institution_approved_modules',
    db.Column('institution_id', db.Integer, db.ForeignKey('institution.id')),
    db.Column('module_id', db.Integer, db.ForeignKey('module.id'))
)

class Institution(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(120))    
    creator_id = db.Column(db.Integer, db.ForeignKey(User.id, use_alter=True, name='fk_institution_creator_id'), nullable=False)        #DJG - need , use_alter=True, name='fk_institution_creator_id' to avoid circular join references
    blurb = db.Column(db.String(400), default = "This is some blurb")    
    student_settings_viewable_modules = db.Column(db.SmallInteger, default = VIEW_ALL, nullable=False) 
    view_institution_only_id = db.Column(db.Integer, db.ForeignKey('institution.id'))    

    view_institution_only = db.relationship("Institution", remote_side=[id], backref="institutions_viewing_approved")

    members = db.relationship(User, secondary=institution_members, lazy='dynamic',
        backref=db.backref('institutions_member', lazy='dynamic'))
    
    students = db.relationship(User, primaryjoin="Institution.id==User.institution_student_id", backref=db.backref("institution_student"))
    
    approved_modules = db.relationship('Module', secondary=institution_approved_modules, backref='approving_institutions', lazy = 'dynamic')

    def is_member(self, user):
        return self.members.filter(institution_members.c.member_id == user.id).count() > 0

    def is_approved(self, module):
        return self.approved_modules.filter(institution_approved_modules.c.module_id == module.id).count() > 0

    def add_member(self, user):
        if user:
            if not self.is_member(user):
                self.members.append(user)
                message = Message(
                    from_id = self.creator_id,
                    to_id = user.id,
                    subject = "You have been added to the institution " + self.name,
                    body = "You have been added to the institution " + self.name + ". All of your authored material will now appear on the approved list of modules for this institution and you can view the progress of all students of " + self.name + ". Your name will be listed on the institution profile page. If you want to leave this institution go to the institutions section of your profile page and click the button to leave.",
                    sent = datetime.utcnow())
                db.session.add(message)            
            for module in user.live_modules_authored().all():
                if not self.is_approved(module):
                    self.approved_modules.append(module)
            db.session.add(self)
            db.session.commit()
        else:
            pass

    @staticmethod 
    def main_courseme_institution():
        return Institution.query.get(1)
        #DJG - Not robust. Need some way to return the main system institution