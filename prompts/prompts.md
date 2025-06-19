# Build a sample database that includes sample student, teacher, administrator, and school data.

### Each of the tables should be interconnected, meaning that although each role (teacher, student, admin) will have their own tables as well as a dedicated "schools" table, each person or school should have a unique ID that connects students at teachers at the same school.

##### Example:
School: 
Patrick Henry High School (ID 13739)
Mission Bay High School (ID 37332)
Admin: 
Sandra White (ID 432832)
Vichara Labe (ID 00001)
Student:
Hudson Mitchell-Pullman (ID 47822)

Hudson's row in the student table should include the ID of the admins at his school, his school ID, teacher IDs, etc.

### Each student should have a user ID and generated password, and you must also configuration sample authentication database with administrators (connect their auth with the admin table) with a user ID (which should be mirrored in the table that contains that person) and password so they can login. 

### Use the Supabase MCP to modify our existing database, and then output the schema that you created.

The data should be the schools will have their own tab datawith data collection, monitoring, AI-insight, and storage software for primary and secondary schools. It should incorporate a hallpass system to allow school administrators to track students, an interface to plan events and allow students to purchase tickets (integrate with Stripe), allows schools to push out hyper-specific surveys to students based on demographics, a training/onboarding page to help teachers and admin learn the software, track programs at the school, a club page where ASB and approved student organizers can add, manage, and track attendance for clubs, see suggested interventions, and an ID page that automatically generates student IDs.


Build a full-stack hall pass database for high schools using Node.js/React with Vite for quick setup and Shadcn/UI for a streamlined user interface and Framer Motion for nice graphics. Focus on optimizing the user experience to minimize the number of clicks a user must make, places where a user could get lost, etc. Since the target users are typically not exceptionally technically inclined, we want 2to prioritize simplicity and beautiful, functional design over a complicated interface. For the backend, use Python + FastAPI for our functions, edge cases, and eventually, AI analytics. There should be two different user experiences for administrators and students, but when a user signs in, they shouldn't have to select which role they are. Instead, the authentication, which should utilize Supabase JWT authentication through email and password, should POST the user's role ID to the frontend, and that should determine which frontend is displayed to the user. For the admin page, there should be an adaptive sidebar with a toggle button at the top to show and hide the sidebar. On that sidebar, they should be able to navigate to the search page, where they can search for a student by searching either the student's name or ID. As the admin is typing, students who match the search (use fuzzy search on the name, not numbers) should be displayed below the search bar, each with their own card that displays their name, grade and ID number (all fetched from Supabase). Then, if they click on a card, a component page should pop up that is essentially a dashboard for that individual student. It should show all active and past hall passes, their grade, and additional metadata. Keep this page primarily simple for now because we aren't storing lots of different data about students, but at least have it configured so we can easily expand the Supabase schema and connect it to this page. The second option on the sidebar should be an overall  