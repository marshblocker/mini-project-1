# Improvements to the Lottery contract:
#  - buy_ticket is now buy_tickets with an additional parameter n for the
#    number of tickets the user will buy.
#  - update_ticket_cost(new_cost) will update the cost of ticket to new_cost.
#  - update_max_tickets(new_max) will update the maximum number of tickets to
#    new_max.
#
# Both the update_ticket_cost() and update_max_tickets() can only be called by
# the contract admin. The contract admin refers to my own account. If you want to
# originate this contract, make sure to replace the assigned address to the admin
# attribute of the contract and the assigned address to the admin alias in the test()
# function.

import smartpy as sp

class Lottery(sp.Contract):
    def __init__(self):
        self.init(
            admin = sp.address("tz1fcNTRug7RXfixJWttCcReTVXSLt2UozSU"),
            players = sp.map(l={}, tkey=sp.TNat, tvalue=sp.TAddress),
            ticket_cost = sp.tez(1),
            tickets_available = sp.nat(5),
            max_tickets = sp.nat(5),
        )

    @sp.entry_point
    def buy_tickets(self, params):
        # params.n : sp.TNat
        #     amount of tickets to be bought.
        sp.set_type(params, sp.TRecord(n=sp.TNat))

        # Sanity checks
        total_cost = sp.mul(params.n, self.data.ticket_cost)
        sp.verify(self.data.tickets_available > 0, "NO TICKETS AVAILABLE")
        sp.verify(sp.amount >= total_cost, "INVALID AMOUNT")
        sp.verify(self.data.tickets_available >= params.n, "REQUESTED AMOUNT OF TICKETS EXCEED THE REMAINING AMOUNT OF TICKETS")

        # Storage updates
        sp.for _ in sp.range(0, params.n, 1):
            self.data.players[sp.len(self.data.players)] = sp.sender
        self.data.tickets_available = sp.as_nat(self.data.tickets_available - params.n)

        # Return extra tez balance to the sender
        extra_balance = sp.amount - total_cost
        sp.if extra_balance > sp.mutez(0):
            sp.send(sp.sender, extra_balance)

    @sp.entry_point
    def update_ticket_cost(self, params):
        # params.new_cost : sp.TNat
        #     updated cost of ticket
        sp.set_type(params, sp.TRecord(new_cost=sp.TMutez))

        # Sanity checks
        sp.verify(
            sp.sender == self.data.admin, 
            "THIS ENTRY POINT CAN ONLY BE CALLED BY THE CONTRACT ADMIN"
        )
        sp.verify(
            self.data.tickets_available == self.data.max_tickets,
            "CANNOT UPDATE TICKET COST WHILE A GAME IS ONGOING"
        )

        # Storage updates
        self.data.ticket_cost = params.new_cost

    @sp.entry_point
    def update_max_tickets(self, params):
        # params.new_max : sp.TNat
        #     updated max number of tickets
        sp.set_type(params, sp.TRecord(new_max = sp.TNat))

        # Sanity checks
        sp.verify(
            sp.sender == self.data.admin, 
            "THIS ENTRY POINT CAN ONLY BE CALLED BY THE CONTRACT ADMIN"
        )
        sp.verify(
            self.data.tickets_available == self.data.max_tickets,
            "CANNOT UPDATE MAXIMUM AMOUNT OF TICKETS WHILE A GAME IS ONGOING"
        )
        sp.verify(
            params.new_max != 0,
            "MAXIMUM AMOUNT OF TICKETS CANNOT BE ZERO"
        )

        # Storage updates
        self.data.max_tickets = params.new_max
        self.data.tickets_available = params.new_max

    @sp.entry_point
    def end_game(self):

        # Sanity checks
        sp.verify(self.data.tickets_available == 0, "GAME IS YET TO END")

        # Pick a winner
        winner_id = sp.as_nat(sp.now - sp.timestamp(0)) % self.data.max_tickets
        winner_address = self.data.players[winner_id]

        # Send the reward to the winner
        sp.send(winner_address, sp.balance)

        # Reset the game
        self.data.players = {}
        self.data.tickets_available = self.data.max_tickets

@sp.add_test(name = "main")
def test():
    scenario = sp.test_scenario()

    # Test accounts
    admin = sp.address("tz1fcNTRug7RXfixJWttCcReTVXSLt2UozSU")
    alice = sp.test_account("alice")
    bob = sp.test_account("bob")
    mike = sp.test_account("mike")
    charles = sp.test_account("charles")
    john = sp.test_account("john")

    # Contract instance
    
    lottery = Lottery()
    scenario += lottery

    # update_ticket_cost
    scenario.h2("Testing update_ticket_cost()")
    
    scenario.h3("Admin updates the ticket cost from 1 tez to 3 tez. (Valid)")
    scenario += lottery.update_ticket_cost(new_cost = sp.tez(3)).run(sender = admin)

    scenario.h3("Non-admin updates the ticket cost. (Invalid)")
    scenario += lottery.update_ticket_cost(new_cost = sp.tez(5)).run(sender = alice, valid = False)

    scenario.h3("Admin updates the ticket cost while a game is ongoing. (Invalid)")
    scenario.h4("First, Bob will buy a ticket.")
    scenario += lottery.buy_tickets(n = 1).run(amount = sp.tez(10), sender = bob)
    scenario.h4("Then, the admin updates the ticket cost while the game is ongoing.")
    scenario += lottery.update_ticket_cost(new_cost = sp.tez(3)).run(sender = admin, valid = False)
    scenario.h4("Let's reset the game by buying all the remaining tickets and call end_game().")
    scenario += lottery.buy_tickets(n = 4).run(amount = sp.tez(20), sender = bob)
    scenario += lottery.end_game().run(sender = admin, now = sp.timestamp(20))

    # update_max_tickets
    scenario.h2("Testing update_max_tickets()")
    
    scenario.h3("Admin updates the maximum tickets from 5 to 10. (Valid)")
    scenario += lottery.update_max_tickets(new_max = sp.nat(10)).run(sender = admin)

    scenario.h3("Non-admin updates the maximum tickets. (Invalid)")
    scenario += lottery.update_max_tickets(new_max = sp.nat(3)).run(sender = alice, valid = False)

    scenario.h3("Admin updates maximum tickets to negative value. (Invalid)")
    scenario += lottery.update_max_tickets(new_max = sp.nat(0)).run(sender = admin, valid = False)

    scenario.h3("Admin updates the maximum tickets while a game is ongoing. (Invalid)")
    scenario.h4("First, Bob will buy a ticket.")
    scenario += lottery.buy_tickets(n = 1).run(amount = sp.tez(10), sender = bob)
    scenario.h4("Then, the admin updates the maximum tickets while the game is ongoing.")
    scenario += lottery.update_max_tickets(new_max = sp.nat(3)).run(sender = admin, valid = False)
    scenario.h4("Let's reset the game by buying all the remaining tickets and call end_game().")
    scenario += lottery.buy_tickets(n = 9).run(amount = sp.tez(100), sender = bob)
    scenario += lottery.end_game().run(sender = admin, now = sp.timestamp(20))

    # buy_tickets and end_game
    scenario.h2("Testing buy_tickets() and end_game()")

    scenario.h3("First, reset max ticket and ticket cost to their original value.")
    scenario += lottery.update_max_tickets(new_max = sp.nat(5)).run(sender = admin)
    scenario += lottery.update_ticket_cost(new_cost = sp.tez(1)).run(sender = admin)

    scenario.h3("Bob will buy two tickets. (Valid)")
    scenario += lottery.buy_tickets(n = 2).run(amount = sp.tez(3), sender = bob)

    scenario.h3("Alice will buy two tickets using only 1 tez. (Invalid)")
    scenario += lottery.buy_tickets(n = 2).run(amount = sp.tez(1), sender = alice, valid = False)

    scenario.h3("Mike will buy more than the available amount of tickets. (Invalid)")
    scenario += lottery.buy_tickets(n = 6).run(amount = sp.tez(10), sender = mike, valid = False)

    scenario.h3("End game when there are still unbought tickets. (Invalid)")
    scenario += lottery.end_game().run(sender = admin, now = sp.timestamp(10), valid = False)

    scenario.h3("Bob will buy the remaining tickets. (Valid)")
    scenario += lottery.buy_tickets(n = 3).run(amount = sp.tez(3), sender = bob)

    scenario.h3("Mike will buy a ticket even though there's no available ticket left. (Invalid)")
    scenario += lottery.buy_tickets(n = 1).run(amount = sp.tez(1), sender = mike, valid = False)

    scenario.h3("End game when all tickets are bought. (Valid)")
    scenario += lottery.end_game().run(sender = admin, now = sp.timestamp(10))
